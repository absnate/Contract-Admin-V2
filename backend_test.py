#!/usr/bin/env python3
"""
Backend API Testing for PDF DocSync Agent
Tests the crawling functionality for americanspecialties.com
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

class BackendTester:
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
                        logger.info(f"API Health Check: {data}")
                        return True
                    else:
                        logger.error(f"API health check failed with status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"API health check failed: {str(e)}")
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
                        logger.info(f"Created crawl job: {job['id']}")
                        return job
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create crawl job: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error creating crawl job: {str(e)}")
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
                        logger.error(f"Failed to get crawl job {job_id}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting crawl job {job_id}: {str(e)}")
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
                        logger.error(f"Failed to get PDFs for job {job_id}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting PDFs for job {job_id}: {str(e)}")
            return None
    
    async def get_stats(self) -> Optional[Dict]:
        """Get API stats"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base}/stats",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get stats: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
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
                        logger.info(f"Cancelled crawl job {job_id}: {result}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to cancel crawl job {job_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error cancelling crawl job {job_id}: {str(e)}")
            return False
    
    async def wait_for_job_completion_or_progress(self, job_id: str, max_wait_seconds: int = 300) -> Dict:
        """Wait for job to complete or make significant progress"""
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < max_wait_seconds:
            # Check API responsiveness by getting stats
            stats = await self.get_stats()
            if stats is None:
                logger.error("API became unresponsive during crawl")
                return {"error": "API unresponsive"}
            
            # Get job status
            job = await self.get_crawl_job(job_id)
            if job is None:
                logger.error(f"Could not retrieve job {job_id}")
                return {"error": "Job not found"}
            
            current_status = job.get('status')
            if current_status != last_status:
                logger.info(f"Job {job_id} status: {current_status} (PDFs found: {job.get('total_pdfs_found', 0)})")
                last_status = current_status
            
            # Check if job is complete or failed
            if current_status in ['completed', 'failed', 'cancelled']:
                return job
            
            # If we've reached classifying and have PDFs, that's sufficient progress
            if current_status == 'classifying' and job.get('total_pdfs_found', 0) > 0:
                logger.info(f"Job reached classifying phase with {job.get('total_pdfs_found')} PDFs found")
                # Wait a bit more to see if classification completes
                await asyncio.sleep(30)
                final_job = await self.get_crawl_job(job_id)
                return final_job or job
            
            await asyncio.sleep(3)  # Poll every 3 seconds
        
        # Timeout reached
        final_job = await self.get_crawl_job(job_id)
        logger.warning(f"Timeout reached after {max_wait_seconds}s. Final status: {final_job.get('status') if final_job else 'unknown'}")
        return final_job or {"error": "Timeout"}

async def run_asi_crawl_test():
    """Run the main ASI crawl test"""
    # Use external API URL from frontend/.env
    base_url = "https://techdoc-spider.preview.emergentagent.com"
    tester = BackendTester(base_url)
    
    logger.info("=== Starting ASI Crawl Test ===")
    
    # Test 1: API Health Check
    logger.info("1. Testing API health...")
    if not await tester.test_api_health():
        logger.error("API health check failed - aborting tests")
        return False
    
    # Test 2: Create crawl job for ASI
    logger.info("2. Creating crawl job for americanspecialties.com...")
    job = await tester.create_crawl_job(
        domain="https://americanspecialties.com/all-washroom-accessories/",
        manufacturer_name="American Specialties (ASI)",
        product_lines=[],
        sharepoint_folder="/DocSyncAgent/Test/ASI"
    )
    
    if not job:
        logger.error("Failed to create crawl job")
        return False
    
    job_id = job['id']
    
    # Test 3: Monitor job progress and API responsiveness
    logger.info("3. Monitoring job progress and API responsiveness...")
    final_job = await tester.wait_for_job_completion_or_progress(job_id, max_wait_seconds=600)  # 10 minutes max
    
    if "error" in final_job:
        logger.error(f"Job monitoring failed: {final_job['error']}")
        return False
    
    # Test 4: Verify PDFs were found
    logger.info("4. Verifying PDFs were found...")
    total_pdfs = final_job.get('total_pdfs_found', 0)
    if total_pdfs == 0:
        logger.error("No PDFs were found during crawl")
        return False
    
    logger.info(f"✓ Found {total_pdfs} PDFs")
    
    # Test 5: Check PDF classification and document types
    logger.info("5. Checking PDF classification...")
    pdfs = await tester.get_job_pdfs(job_id)
    
    if not pdfs:
        logger.error("Could not retrieve PDF records")
        return False
    
    # Check for expected document types
    expected_types = ["Product Data Sheet", "Specification Sheet", "Submittal Sheet", "Technical Data Sheet"]
    found_types = set()
    installation_manuals_uploaded = 0
    
    for pdf in pdfs:
        doc_type = pdf.get('document_type')
        if doc_type:
            found_types.add(doc_type)
        
        # Check that Installation Manuals are NOT uploaded
        if doc_type == "Installation Manual" and pdf.get('sharepoint_uploaded', False):
            installation_manuals_uploaded += 1
    
    logger.info(f"Found document types: {list(found_types)}")
    
    # Verify we have some expected document types
    expected_found = [t for t in expected_types if t in found_types]
    if not expected_found:
        logger.error(f"No expected document types found. Expected: {expected_types}, Found: {list(found_types)}")
        return False
    
    logger.info(f"✓ Found expected document types: {expected_found}")
    
    # Verify Installation Manuals are not uploaded
    if installation_manuals_uploaded > 0:
        logger.error(f"❌ {installation_manuals_uploaded} Installation Manuals were uploaded (should be 0)")
        return False
    
    logger.info("✓ Installation Manuals correctly excluded from upload")
    
    logger.info("=== ASI Crawl Test PASSED ===")
    return True

async def run_cancellation_test():
    """Test job cancellation functionality"""
    base_url = "https://techdoc-spider.preview.emergentagent.com"
    tester = BackendTester(base_url)
    
    logger.info("=== Starting Cancellation Test ===")
    
    # Create a job to cancel
    logger.info("1. Creating crawl job for cancellation test...")
    job = await tester.create_crawl_job(
        domain="https://americanspecialties.com/all-washroom-accessories/",
        manufacturer_name="American Specialties (ASI) - Cancel Test",
        product_lines=[],
        sharepoint_folder="/DocSyncAgent/Test/ASI-Cancel"
    )
    
    if not job:
        logger.error("Failed to create crawl job for cancellation test")
        return False
    
    job_id = job['id']
    
    # Wait a moment for job to start
    await asyncio.sleep(5)
    
    # Cancel the job
    logger.info("2. Cancelling the crawl job...")
    if not await tester.cancel_crawl_job(job_id):
        logger.error("Failed to cancel crawl job")
        return False
    
    # Verify job status becomes cancelled
    logger.info("3. Verifying job status becomes cancelled...")
    await asyncio.sleep(2)
    
    cancelled_job = await tester.get_crawl_job(job_id)
    if not cancelled_job:
        logger.error("Could not retrieve cancelled job")
        return False
    
    if cancelled_job.get('status') != 'cancelled':
        logger.error(f"Job status is {cancelled_job.get('status')}, expected 'cancelled'")
        return False
    
    logger.info("✓ Job successfully cancelled")
    
    # Monitor for a bit to ensure no continued progress
    logger.info("4. Monitoring to ensure crawl process stops...")
    await asyncio.sleep(10)
    
    final_job = await tester.get_crawl_job(job_id)
    if final_job and final_job.get('status') == 'cancelled':
        logger.info("✓ Job remains cancelled - no continued progress")
        logger.info("=== Cancellation Test PASSED ===")
        return True
    else:
        logger.error("Job status changed after cancellation")
        return False

async def main():
    """Run all backend tests"""
    logger.info("Starting Backend API Tests for PDF DocSync Agent")
    
    try:
        # Run main crawl test
        crawl_success = await run_asi_crawl_test()
        
        # Run cancellation test
        cancel_success = await run_cancellation_test()
        
        # Summary
        logger.info("\n=== TEST SUMMARY ===")
        logger.info(f"ASI Crawl Test: {'PASSED' if crawl_success else 'FAILED'}")
        logger.info(f"Cancellation Test: {'PASSED' if cancel_success else 'FAILED'}")
        
        if crawl_success and cancel_success:
            logger.info("🎉 ALL TESTS PASSED")
            return True
        else:
            logger.error("❌ SOME TESTS FAILED")
            return False
            
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)