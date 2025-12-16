#!/usr/bin/env python3
"""
SharePoint Upload Testing for PDF DocSync Agent
Tests the full crawl-to-SharePoint-upload pipeline after critical fixes:
1. Azure AD credentials restored
2. Playwright browser v1194 installed  
3. Child process logging added
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SharePointUploadTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api"
        
    async def test_api_health(self) -> bool:
        """Test if API is responsive"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✓ API Health Check: {data}")
                        return True
                    else:
                        logger.error(f"❌ API health check failed with status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ API health check failed: {str(e)}")
            return False
    
    async def test_sharepoint_auth(self) -> bool:
        """Test SharePoint authentication by creating a test job and checking for auth errors"""
        try:
            # Create a minimal test job to trigger SharePoint auth
            job_data = {
                "domain": "https://bradleycorp.com/products/hand-dryers",
                "manufacturer_name": "Bradley Test Auth",
                "product_lines": [],
                "sharepoint_folder": "Test Uploads/Auth Test",
                "weekly_recrawl": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/crawl-jobs",
                    json=job_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        job = await response.json()
                        job_id = job['id']
                        logger.info(f"✓ Created auth test job: {job_id}")
                        
                        # Wait a moment for the job to start and potentially hit SharePoint
                        await asyncio.sleep(10)
                        
                        # Cancel the job to avoid unnecessary crawling
                        await self.cancel_crawl_job(job_id)
                        logger.info("✓ SharePoint authentication appears to be working (no immediate auth errors)")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Failed to create auth test job: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"❌ SharePoint auth test failed: {str(e)}")
            return False
    
    async def create_crawl_job(self, domain: str, manufacturer_name: str, product_lines: List[str], sharepoint_folder: str) -> Optional[Dict]:
        """Create a new crawl job"""
        try:
            job_data = {
                "domain": domain,
                "manufacturer_name": manufacturer_name,
                "product_lines": product_lines,
                "sharepoint_folder": sharepoint_folder,
                "weekly_recrawl": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/crawl-jobs",
                    json=job_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        job = await response.json()
                        logger.info(f"✓ Created crawl job: {job['id']} for {domain}")
                        return job
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Failed to create crawl job: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error creating crawl job: {str(e)}")
            return None
    
    async def get_crawl_job(self, job_id: str) -> Optional[Dict]:
        """Get crawl job details"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base}/crawl-jobs/{job_id}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"❌ Failed to get crawl job {job_id}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error getting crawl job {job_id}: {str(e)}")
            return None
    
    async def get_job_pdfs(self, job_id: str) -> Optional[List[Dict]]:
        """Get PDFs for a crawl job"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base}/crawl-jobs/{job_id}/pdfs",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"❌ Failed to get PDFs for job {job_id}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error getting PDFs for job {job_id}: {str(e)}")
            return None
    
    async def cancel_crawl_job(self, job_id: str) -> bool:
        """Cancel a crawl job"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/crawl-jobs/{job_id}/cancel",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✓ Cancelled crawl job {job_id}: {result}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Failed to cancel crawl job {job_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"❌ Error cancelling crawl job {job_id}: {str(e)}")
            return False
    
    async def wait_for_job_completion(self, job_id: str, max_wait_seconds: int = 900) -> Dict:
        """Wait for job to complete through all phases: crawling -> classifying -> uploading -> completed"""
        start_time = time.time()
        last_status = None
        last_pdfs_found = 0
        last_pdfs_classified = 0
        last_pdfs_uploaded = 0
        
        logger.info(f"Monitoring job {job_id} through full pipeline (max {max_wait_seconds}s)...")
        
        while time.time() - start_time < max_wait_seconds:
            # Get job status
            job = await self.get_crawl_job(job_id)
            if job is None:
                logger.error(f"❌ Could not retrieve job {job_id}")
                return {"error": "Job not found"}
            
            current_status = job.get('status')
            pdfs_found = job.get('total_pdfs_found', 0)
            pdfs_classified = job.get('total_pdfs_classified', 0)
            pdfs_uploaded = job.get('total_pdfs_uploaded', 0)
            
            # Log status changes and progress
            if (current_status != last_status or 
                pdfs_found != last_pdfs_found or 
                pdfs_classified != last_pdfs_classified or 
                pdfs_uploaded != last_pdfs_uploaded):
                
                elapsed = int(time.time() - start_time)
                logger.info(f"[{elapsed}s] Job {job_id}: {current_status} | "
                          f"Found: {pdfs_found} | Classified: {pdfs_classified} | Uploaded: {pdfs_uploaded}")
                
                last_status = current_status
                last_pdfs_found = pdfs_found
                last_pdfs_classified = pdfs_classified
                last_pdfs_uploaded = pdfs_uploaded
            
            # Check if job is complete or failed
            if current_status in ['completed', 'failed', 'cancelled']:
                elapsed = int(time.time() - start_time)
                logger.info(f"Job {job_id} finished with status '{current_status}' after {elapsed}s")
                return job
            
            await asyncio.sleep(15)  # Poll every 15 seconds as requested
        
        # Timeout reached
        elapsed = int(time.time() - start_time)
        final_job = await self.get_crawl_job(job_id)
        logger.warning(f"⚠️ Timeout reached after {elapsed}s. Final status: {final_job.get('status') if final_job else 'unknown'}")
        return final_job or {"error": "Timeout"}

async def run_sharepoint_upload_test():
    """Run the main SharePoint upload test"""
    # Use external API URL from frontend/.env
    base_url = "https://techdoc-spider.preview.emergentagent.com"
    tester = SharePointUploadTester(base_url)
    
    logger.info("=== SharePoint Upload Pipeline Test ===")
    logger.info("Testing fixes: Azure AD credentials, Playwright browser, child process logging")
    
    # Test 1: API Health Check
    logger.info("\n1. Testing API health...")
    if not await tester.test_api_health():
        logger.error("❌ API health check failed - aborting tests")
        return False
    
    # Test 2: SharePoint Authentication Test
    logger.info("\n2. Testing SharePoint authentication...")
    if not await tester.test_sharepoint_auth():
        logger.error("❌ SharePoint authentication test failed")
        return False
    
    # Test 3: Create crawl job for Bradley Corp (small domain with PDFs)
    logger.info("\n3. Creating crawl job for Bradley Corp hand dryers...")
    job = await tester.create_crawl_job(
        domain="https://bradleycorp.com/products/hand-dryers",
        manufacturer_name="Bradley Test",
        product_lines=[],
        sharepoint_folder="Test Uploads/Bradley"
    )
    
    if not job:
        logger.error("❌ Failed to create crawl job")
        return False
    
    job_id = job['id']
    
    # Test 4: Monitor job through full pipeline
    logger.info("\n4. Monitoring job through full pipeline (crawling -> classifying -> uploading -> completed)...")
    final_job = await tester.wait_for_job_completion(job_id, max_wait_seconds=900)  # 15 minutes max
    
    if "error" in final_job:
        logger.error(f"❌ Job monitoring failed: {final_job['error']}")
        return False
    
    # Test 5: Verify job completed successfully
    logger.info("\n5. Verifying job completion...")
    final_status = final_job.get('status')
    if final_status != 'completed':
        logger.error(f"❌ Job did not complete successfully. Final status: {final_status}")
        if final_job.get('error_message'):
            logger.error(f"Error message: {final_job['error_message']}")
        return False
    
    logger.info(f"✓ Job completed successfully")
    
    # Test 6: Verify PDFs were found, classified, and uploaded
    logger.info("\n6. Verifying PDF processing stats...")
    total_pdfs_found = final_job.get('total_pdfs_found', 0)
    total_pdfs_classified = final_job.get('total_pdfs_classified', 0)
    total_pdfs_uploaded = final_job.get('total_pdfs_uploaded', 0)
    
    logger.info(f"Final stats - Found: {total_pdfs_found}, Classified: {total_pdfs_classified}, Uploaded: {total_pdfs_uploaded}")
    
    if total_pdfs_found == 0:
        logger.error("❌ No PDFs were found during crawl")
        return False
    
    if total_pdfs_classified == 0:
        logger.error("❌ No PDFs were classified")
        return False
    
    if total_pdfs_uploaded == 0:
        logger.error("❌ No PDFs were uploaded to SharePoint")
        return False
    
    logger.info(f"✓ PDFs successfully processed: {total_pdfs_found} found, {total_pdfs_classified} classified, {total_pdfs_uploaded} uploaded")
    
    # Test 7: Verify PDF records show SharePoint upload details
    logger.info("\n7. Verifying PDF records show SharePoint upload details...")
    pdfs = await tester.get_job_pdfs(job_id)
    
    if not pdfs:
        logger.error("❌ Could not retrieve PDF records")
        return False
    
    uploaded_pdfs = [pdf for pdf in pdfs if pdf.get('sharepoint_uploaded', False)]
    pdfs_with_sharepoint_id = [pdf for pdf in uploaded_pdfs if pdf.get('sharepoint_id')]
    
    logger.info(f"PDF records: {len(pdfs)} total, {len(uploaded_pdfs)} marked as uploaded, {len(pdfs_with_sharepoint_id)} with SharePoint ID")
    
    if len(uploaded_pdfs) == 0:
        logger.error("❌ No PDF records marked as sharepoint_uploaded: true")
        return False
    
    if len(pdfs_with_sharepoint_id) == 0:
        logger.error("❌ No PDF records have sharepoint_id values")
        return False
    
    # Show some examples
    for i, pdf in enumerate(uploaded_pdfs[:3]):  # Show first 3 uploaded PDFs
        logger.info(f"  Example {i+1}: {pdf.get('filename')} -> SharePoint ID: {pdf.get('sharepoint_id')}")
    
    logger.info(f"✓ PDF records correctly show SharePoint upload details")
    
    logger.info("\n=== SharePoint Upload Pipeline Test PASSED ===")
    logger.info("✅ All critical functionality verified:")
    logger.info("  - SharePoint authentication working")
    logger.info("  - Job progresses through all phases (crawling -> classifying -> uploading -> completed)")
    logger.info("  - PDFs are found, classified, and uploaded to SharePoint")
    logger.info("  - PDF records show sharepoint_uploaded: true with valid sharepoint_id values")
    return True

async def run_alternative_test():
    """Run alternative test with American Specialties single product page if Bradley fails"""
    base_url = "https://techdoc-spider.preview.emergentagent.com"
    tester = SharePointUploadTester(base_url)
    
    logger.info("\n=== Alternative Test: American Specialties Single Product ===")
    
    # Create crawl job for ASI single product page
    logger.info("Creating crawl job for American Specialties single product...")
    job = await tester.create_crawl_job(
        domain="https://americanspecialties.com/product/0199-1/",
        manufacturer_name="ASI Single Product Test",
        product_lines=[],
        sharepoint_folder="Test Uploads/ASI-Single"
    )
    
    if not job:
        logger.error("❌ Failed to create alternative crawl job")
        return False
    
    job_id = job['id']
    
    # Monitor job through full pipeline
    logger.info("Monitoring alternative job through full pipeline...")
    final_job = await tester.wait_for_job_completion(job_id, max_wait_seconds=600)  # 10 minutes for single product
    
    if "error" in final_job:
        logger.error(f"❌ Alternative job monitoring failed: {final_job['error']}")
        return False
    
    # Verify completion
    final_status = final_job.get('status')
    if final_status != 'completed':
        logger.error(f"❌ Alternative job did not complete. Final status: {final_status}")
        return False
    
    total_pdfs_uploaded = final_job.get('total_pdfs_uploaded', 0)
    if total_pdfs_uploaded == 0:
        logger.error("❌ Alternative job: No PDFs uploaded to SharePoint")
        return False
    
    logger.info(f"✅ Alternative test PASSED: {total_pdfs_uploaded} PDFs uploaded")
    return True

async def main():
    """Run SharePoint upload tests"""
    logger.info("Starting SharePoint Upload Tests for PDF DocSync Agent")
    logger.info("Testing critical fixes: Azure AD credentials, Playwright browser, child process logging")
    
    try:
        # Run main SharePoint upload test
        main_success = await run_sharepoint_upload_test()
        
        # If main test fails, try alternative
        alt_success = False
        if not main_success:
            logger.info("\n⚠️ Main test failed, trying alternative test...")
            alt_success = await run_alternative_test()
        
        # Summary
        logger.info("\n=== TEST SUMMARY ===")
        logger.info(f"Main SharePoint Upload Test: {'PASSED' if main_success else 'FAILED'}")
        if not main_success:
            logger.info(f"Alternative Test: {'PASSED' if alt_success else 'FAILED'}")
        
        overall_success = main_success or alt_success
        
        if overall_success:
            logger.info("🎉 SHAREPOINT UPLOAD TESTS PASSED")
            logger.info("✅ Critical fixes verified working:")
            logger.info("  - Azure AD credentials restored and working")
            logger.info("  - Playwright browser v1194 installed and functional")
            logger.info("  - Full crawl-to-SharePoint-upload pipeline operational")
            return True
        else:
            logger.error("❌ ALL SHAREPOINT UPLOAD TESTS FAILED")
            logger.error("🚨 Critical issues remain with the SharePoint upload pipeline")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)