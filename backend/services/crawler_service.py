import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import List, Set
from datetime import datetime, timezone
from .pdf_classifier import PDFClassifier
from .sharepoint_service import SharePointService

logger = logging.getLogger(__name__)

class CrawlerService:
    def __init__(self, db):
        self.db = db
        self.pdf_classifier = PDFClassifier()
        self.sharepoint_service = SharePointService()
        self.visited_urls: Set[str] = set()
        self.pdf_urls: Set[str] = set()
        
    async def start_crawl(self, job_id: str, domain: str, product_lines: List[str], manufacturer_name: str, sharepoint_folder: str):
        """Start crawling a domain for PDFs"""
        try:
            logger.info(f"Starting crawl for job {job_id} on domain {domain}")
            
            # Update job status
            await self._update_job_status(job_id, "crawling")
            
            # Crawl the domain
            pdf_links = await self._crawl_domain(domain, product_lines, max_pages=100)
            
            logger.info(f"Found {len(pdf_links)} PDF links for job {job_id}")
            
            # Update job with found PDFs count
            await self.db.crawl_jobs.update_one(
                {"id": job_id},
                {"$set": {"total_pdfs_found": len(pdf_links), "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            # Classify PDFs
            await self._update_job_status(job_id, "classifying")
            await self._classify_pdfs(job_id, pdf_links, product_lines, manufacturer_name)
            
            # Upload to SharePoint
            await self._update_job_status(job_id, "uploading")
            await self._upload_to_sharepoint(job_id, sharepoint_folder)
            
            # Mark as completed
            await self._update_job_status(job_id, "completed")
            logger.info(f"Crawl job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error in crawl job {job_id}: {str(e)}")
            await self.db.crawl_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "failed",
                    "error_message": str(e),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    
    async def _crawl_domain(self, domain: str, product_lines: List[str], max_pages: int = 500) -> Set[str]:
        """Crawl a domain to find PDF links"""
        self.visited_urls.clear()
        self.pdf_urls.clear()
        
        # Ensure domain has protocol
        if not domain.startswith(('http://', 'https://')):
            domain = f'https://{domain}'
        
        base_domain = urlparse(domain).netloc
        
        logger.info(f"Starting crawl of {base_domain} with max {max_pages} pages")
        
        async with aiohttp.ClientSession() as session:
            await self._crawl_page(session, domain, base_domain, product_lines, max_pages)
        
        logger.info(f"Crawl completed: visited {len(self.visited_urls)} pages, found {len(self.pdf_urls)} PDFs")
        return self.pdf_urls
    
    async def _crawl_page(self, session: aiohttp.ClientSession, url: str, base_domain: str, product_lines: List[str], max_pages: int):
        """Recursively crawl a page for PDFs and links"""
        if len(self.visited_urls) >= max_pages or url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        
        # Log progress every 10 pages
        if len(self.visited_urls) % 10 == 0:
            logger.info(f"Crawl progress: {len(self.visited_urls)} pages visited, {len(self.pdf_urls)} PDFs found")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30), allow_redirects=True, headers=headers) as response:
                if response.status != 200:
                    logger.debug(f"Skipping {url} - Status {response.status}")
                    return
                
                content_type = response.headers.get('content-type', '').lower()
                
                # If it's a PDF, add it
                if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
                    if self._matches_product_lines(url, '', product_lines):
                        self.pdf_urls.add(url)
                        logger.info(f"Found PDF: {url}")
                    return
                
                # Only process HTML pages
                if 'text/html' not in content_type:
                    return
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find all links
                links_to_crawl = []
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    full_url = urljoin(url, href)
                    
                    # Skip anchors, javascript, mailto, tel
                    if full_url.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                        continue
                    
                    # Remove URL fragments
                    full_url = full_url.split('#')[0]
                    
                    # Check if it's a PDF
                    if full_url.lower().endswith('.pdf'):
                        # Check if it matches product lines (if specified)
                        if self._matches_product_lines(full_url, link.get_text(), product_lines):
                            self.pdf_urls.add(full_url)
                            logger.info(f"Found PDF: {full_url}")
                        continue
                    
                    # Only follow links within the same domain
                    if urlparse(full_url).netloc == base_domain and full_url not in self.visited_urls:
                        # Check if URL might lead to product documentation
                        if self._is_relevant_url(full_url, product_lines):
                            links_to_crawl.append(full_url)
                
                # Crawl collected links
                for next_url in links_to_crawl[:5]:  # Limit breadth to avoid too many branches
                    if len(self.visited_urls) < max_pages:
                        await asyncio.sleep(0.5)  # Be polite
                        await self._crawl_page(session, next_url, base_domain, product_lines, max_pages)
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout crawling {url}")
        except Exception as e:
            logger.warning(f"Error crawling {url}: {str(e)}")
    
    def _matches_product_lines(self, url: str, link_text: str, product_lines: List[str]) -> bool:
        """Check if URL or link text matches any product lines"""
        if not product_lines:
            return True
        
        combined_text = f"{url} {link_text}".lower()
        return any(pl.lower() in combined_text for pl in product_lines)
    
    def _is_relevant_url(self, url: str, product_lines: List[str]) -> bool:
        """Check if URL is likely to contain technical documentation"""
        url_lower = url.lower()
        
        # Expanded list of relevant keywords for manufacturer sites
        relevant_keywords = [
            'product', 'document', 'download', 'resource', 'support', 'technical', 
            'data', 'spec', 'manual', 'pdf', 'literature', 'catalog', 'media',
            'file', 'doc', 'sheet', 'library', 'asset', 'datasheet', 'brochure',
            'install', 'guide', 'submittal'
        ]
        
        # URLs to avoid (common site structure that won't have PDFs)
        avoid_keywords = [
            'login', 'cart', 'checkout', 'account', 'register', 'signin',
            'facebook', 'twitter', 'linkedin', 'youtube', 'instagram',
            'privacy', 'terms', 'cookie', 'sitemap', 'search', 'contact',
            'blog', 'news', 'press', 'careers', 'jobs'
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
        
        # If no product lines specified, accept any relevant URL
        # If product lines specified, also accept URLs with relevant keywords
        return has_relevant_keyword or not product_lines
    
    async def _classify_pdfs(self, job_id: str, pdf_links: Set[str], product_lines: List[str], manufacturer_name: str):
        """Classify PDFs using AI"""
        classified_count = 0
        
        # Convert set to list to avoid "set changed size during iteration" error
        pdf_links_list = list(pdf_links)
        logger.info(f"Starting classification of {len(pdf_links_list)} PDFs")
        
        for pdf_url in pdf_links_list:
            try:
                # Download PDF metadata (first few KB)
                async with aiohttp.ClientSession() as session:
                    async with session.get(pdf_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            # Get filename and file size
                            filename = pdf_url.split('/')[-1]
                            file_size = int(response.headers.get('content-length', 0))
                            
                            # Read first 100KB for classification
                            content_sample = await response.content.read(102400)
                            
                            # Classify using AI
                            classification = await self.pdf_classifier.classify_pdf(
                                filename=filename,
                                url=pdf_url,
                                content_sample=content_sample,
                                manufacturer=manufacturer_name,
                                product_lines=product_lines
                            )
                            
                            # Save PDF record
                            pdf_record = {
                                "id": str(datetime.now(timezone.utc).timestamp()).replace('.', ''),
                                "job_id": job_id,
                                "filename": filename,
                                "source_url": pdf_url,
                                "file_size": file_size,
                                "is_technical": classification['is_technical'],
                                "classification_reason": classification['reason'],
                                "document_type": classification.get('document_type'),
                                "sharepoint_uploaded": False,
                                "sharepoint_id": None,
                                "created_at": datetime.now(timezone.utc).isoformat()
                            }
                            
                            await self.db.pdf_records.insert_one(pdf_record)
                            classified_count += 1
                            
                            logger.info(f"Classified PDF: {filename} - Technical: {classification['is_technical']}")
            
            except Exception as e:
                logger.error(f"Error classifying PDF {pdf_url}: {str(e)}")
        
        # Update job with classified count
        await self.db.crawl_jobs.update_one(
            {"id": job_id},
            {"$set": {"total_pdfs_classified": classified_count, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    async def _upload_to_sharepoint(self, job_id: str, sharepoint_folder: str):
        """Upload technical PDFs to SharePoint"""
        # Get all technical PDFs for this job
        technical_pdfs = await self.db.pdf_records.find({
            "job_id": job_id,
            "is_technical": True,
            "sharepoint_uploaded": False
        }).to_list(1000)
        
        uploaded_count = 0
        
        for pdf in technical_pdfs:
            try:
                # Download PDF
                async with aiohttp.ClientSession() as session:
                    async with session.get(pdf['source_url'], timeout=aiohttp.ClientTimeout(total=60)) as response:
                        if response.status == 200:
                            pdf_content = await response.read()
                            
                            # Upload to SharePoint
                            sharepoint_id = await self.sharepoint_service.upload_pdf(
                                filename=pdf['filename'],
                                content=pdf_content,
                                folder_path=sharepoint_folder
                            )
                            
                            # Update PDF record
                            await self.db.pdf_records.update_one(
                                {"id": pdf['id']},
                                {"$set": {
                                    "sharepoint_uploaded": True,
                                    "sharepoint_id": sharepoint_id
                                }}
                            )
                            
                            uploaded_count += 1
                            logger.info(f"Uploaded PDF to SharePoint: {pdf['filename']}")
            
            except Exception as e:
                logger.error(f"Error uploading PDF {pdf['filename']} to SharePoint: {str(e)}")
        
        # Update job with uploaded count
        await self.db.crawl_jobs.update_one(
            {"id": job_id},
            {"$set": {"total_pdfs_uploaded": uploaded_count, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    async def _update_job_status(self, job_id: str, status: str):
        """Update job status"""
        await self.db.crawl_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )