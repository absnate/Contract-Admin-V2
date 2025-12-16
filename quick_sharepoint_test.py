#!/usr/bin/env python3
"""
Quick SharePoint Upload Test
Tests a smaller domain for faster results
"""

import asyncio
import aiohttp
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def quick_test():
    base_url = "https://techdoc-spider.preview.emergentagent.com"
    
    # Test API health
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/api/", timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                logger.error("API health check failed")
                return False
            logger.info("✓ API is healthy")
    
    # Create a job for ASI single product (smaller, faster)
    job_data = {
        "domain": "https://americanspecialties.com/product/0199-1/",
        "manufacturer_name": "ASI Quick Test",
        "product_lines": [],
        "sharepoint_folder": "Test Uploads/ASI-Quick",
        "weekly_recrawl": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{base_url}/api/crawl-jobs", json=job_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Failed to create job: {response.status} - {error_text}")
                return False
            
            job = await response.json()
            job_id = job['id']
            logger.info(f"✓ Created job: {job_id}")
    
    # Monitor for 5 minutes
    start_time = time.time()
    while time.time() - start_time < 300:  # 5 minutes
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/crawl-jobs/{job_id}", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    job = await response.json()
                    status = job.get('status')
                    pdfs_found = job.get('total_pdfs_found', 0)
                    pdfs_classified = job.get('total_pdfs_classified', 0)
                    pdfs_uploaded = job.get('total_pdfs_uploaded', 0)
                    
                    elapsed = int(time.time() - start_time)
                    logger.info(f"[{elapsed}s] Status: {status} | Found: {pdfs_found} | Classified: {pdfs_classified} | Uploaded: {pdfs_uploaded}")
                    
                    if status == 'completed':
                        if pdfs_uploaded > 0:
                            logger.info(f"✅ SUCCESS: Job completed with {pdfs_uploaded} PDFs uploaded to SharePoint")
                            return True
                        else:
                            logger.error(f"❌ Job completed but no PDFs uploaded")
                            return False
                    elif status == 'failed':
                        error_msg = job.get('error_message', 'Unknown error')
                        logger.error(f"❌ Job failed: {error_msg}")
                        return False
        
        await asyncio.sleep(15)
    
    logger.warning("⚠️ Test timed out after 5 minutes")
    return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    print(f"Result: {'PASSED' if success else 'FAILED'}")