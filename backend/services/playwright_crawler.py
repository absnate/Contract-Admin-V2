import asyncio
import logging
import os
from typing import Set, List
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Page, Browser
import re

logger = logging.getLogger(__name__)

# Set Playwright browser path
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'

class PlaywrightCrawler:
    def __init__(self, cancel_check=None):
        self.visited_urls: Set[str] = set()
        self.pdf_urls: Set[str] = set()
        self.browser: Browser = None
        self.playwright = None
        self._cancel_check = cancel_check
    async def _should_cancel(self) -> bool:
        if not self._cancel_check:
            return False
        try:
            return bool(await self._cancel_check())
        except Exception:
            return False


    
    async def crawl_domain(self, domain: str, product_lines: List[str], max_pages: int = 100) -> Set[str]:
        """Crawl a JavaScript-heavy domain using Playwright"""
        self.visited_urls.clear()
        self.pdf_urls.clear()

        if await self._should_cancel():
            logger.info("Playwright crawl cancelled before start")
            return set()
        
        # Ensure domain has protocol
        if not domain.startswith(('http://', 'https://')):
            domain = f'https://{domain}'
        
        base_domain = urlparse(domain).netloc
        
        logger.info(f"Starting Playwright crawl of {base_domain} with max {max_pages} pages")
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            
            await self._crawl_page_with_browser(domain, base_domain, product_lines, max_pages)
            
            logger.info(f"Playwright crawl completed: visited {len(self.visited_urls)} pages, found {len(self.pdf_urls)} PDFs")
        
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        
        return self.pdf_urls
    
    async def _crawl_page_with_browser(self, url: str, base_domain: str, product_lines: List[str], max_pages: int):
        """Crawl a page using Playwright browser"""
        if await self._should_cancel():
            return

        if len(self.visited_urls) >= max_pages or url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        
        # Log progress (kept minimal here; detailed progress is logged after processing each page)
        if len(self.visited_urls) % 20 == 0:
            logger.info(f"Playwright crawl progress: {len(self.visited_urls)} pages visited, {len(self.pdf_urls)} PDFs found")
        
        try:
            page = await self.browser.new_page()
            
            # If the URL itself is a document, don't navigate (it can trigger Playwright download mode)
            url_path_lower = urlparse(url).path.lower()
            if url_path_lower.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx')):
                self.pdf_urls.add(url)
                await page.close()
                return

            # Navigate to page with longer timeout and domcontentloaded instead of networkidle
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception:
                # If timeout, try with load instead
                logger.debug(f"Timeout with domcontentloaded, trying load: {url}")
                await page.goto(url, wait_until="load", timeout=60000)
            
            # Wait for content to load
            await page.wait_for_timeout(1500)
            
            # Find all links on the page
            links = await page.query_selector_all('a[href]')

            def _url_priority(candidate_url: str, candidate_text: str) -> int:
                u = (candidate_url or "").lower()
                t = (candidate_text or "").lower()

                score = 0

                # Product/category pages (WordPress/WooCommerce common patterns)
                if "/product/" in u:
                    score += 1000
                if "/product_category/" in u:
                    score += 800

                # Documentation/library pages
                if "technical-data" in u or "/tds" in u or "data-sheet" in u or "datasheet" in u:
                    score += 600
                if "product-data" in u:
                    score += 580
                if "submittal" in u:
                    score += 550
                if "spec" in u:
                    score += 500

                # De-prioritize translated duplicates
                if re.search(r"https?://[^/]+/(fr|es|de|hi|ar)/", u):
                    score -= 600

                # Link text hints
                if any(k in t for k in ["technical data", "data sheet", "datasheet", "product data", "submittal", "spec"]):
                    score += 200

                return score

            url_scores = {}

            for link in links:
                try:
                    href = await link.get_attribute('href')
                    if not href:
                        continue

                    # Skip anchors, javascript, mailto, tel
                    if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                        continue

                    full_url = urljoin(url, href)

                    # Remove fragments
                    full_url = full_url.split('#')[0]

                    # Check if it's a document link (handle query strings like .pdf?ver=...)
                    path_lower = urlparse(full_url).path.lower()
                    if (
                        path_lower.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'))
                        or '/view/' in full_url
                        or '/mediamanager/' in full_url
                    ):
                        link_text = await link.inner_text() if link else ''
                        if self._matches_product_lines(full_url, link_text, product_lines):
                            self.pdf_urls.add(full_url)
                            logger.debug(f"Found document: {full_url}")
                        continue

                    # Only follow links within same domain
                    if urlparse(full_url).netloc == base_domain and full_url not in self.visited_urls:
                        # Check if URL is relevant
                        if self._is_relevant_url(full_url, product_lines):
                            link_text = await link.inner_text() if link else ''
                            score = _url_priority(full_url, link_text)
                            url_scores[full_url] = max(url_scores.get(full_url, -10**9), score)

                except Exception as e:
                    logger.debug(f"Error processing link: {str(e)}")

            await page.close()

            sorted_urls = sorted(url_scores.items(), key=lambda kv: kv[1], reverse=True)
            top_k = 15
            urls_to_crawl = [u for u, _ in sorted_urls[:top_k]]

            # Crawl collected URLs (limit breadth)
            for next_url in urls_to_crawl:
                if await self._should_cancel():
                    return

                if len(self.visited_urls) < max_pages:
                    await asyncio.sleep(1)  # Be polite
                    await self._crawl_page_with_browser(next_url, base_domain, product_lines, max_pages)

            if len(self.visited_urls) % 5 == 0:
                logger.info(
                    f"Playwright crawl progress: {len(self.visited_urls)} pages visited, {len(self.pdf_urls)} PDFs found"
                )
        
        except Exception as e:
            logger.warning(f"Error crawling {url} with Playwright: {str(e)}")
    
    def _matches_product_lines(self, url: str, link_text: str, product_lines: List[str]) -> bool:
        """Check if URL or link text matches any product lines"""
        if not product_lines:
            return True
        
        combined_text = f"{url} {link_text}".lower()
        return any(pl.lower() in combined_text for pl in product_lines)
    
    def _is_relevant_url(self, url: str, product_lines: List[str]) -> bool:
        """Check if URL is likely to contain product documentation"""
        url_lower = url.lower()
        
        # Relevant keywords for product pages and documentation
        relevant_keywords = [
            'product', 'item', 'part', 'model', 'sku',
            'document', 'download', 'resource', 'support', 'technical', 
            'data', 'spec', 'manual', 'pdf', 'literature', 'catalog', 'media',
            'file', 'doc', 'sheet', 'library', 'asset', 'datasheet', 'brochure',
            'install', 'guide', 'submittal', 'category', 'series'
        ]
        
        # URLs to avoid
        avoid_keywords = [
            'login', 'cart', 'checkout', 'account', 'register', 'signin',
            'facebook', 'twitter', 'linkedin', 'youtube', 'instagram',
            'privacy', 'terms', 'cookie', 'sitemap', 'search?', 'contact',
            'blog', 'news', 'press', 'careers', 'jobs', 'about-us'
        ]
        
        # Skip URLs with avoid keywords
        if any(avoid in url_lower for avoid in avoid_keywords):
            return False
        
        # If product lines specified, prioritize URLs containing them
        if product_lines:
            matches_product = any(pl.lower() in url_lower for pl in product_lines)
            if matches_product:
                return True
        
        # Check if URL contains relevant keywords
        has_relevant_keyword = any(keyword in url_lower for keyword in relevant_keywords)
        
        return has_relevant_keyword or not product_lines
