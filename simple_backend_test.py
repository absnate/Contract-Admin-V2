#!/usr/bin/env python3
"""
Simple Backend API Test for PDF DocSync Agent
Tests the key functionality for americanspecialties.com crawling
"""

import requests
import json
import time
import sys

BASE_URL = "https://pdfharvester-1.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

def test_api_health():
    """Test if API is responsive"""
    try:
        response = requests.get(f"{API_BASE}/", timeout=10)
        if response.status_code == 200:
            print("✓ API Health Check: PASSED")
            return True
        else:
            print(f"❌ API Health Check: FAILED (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ API Health Check: FAILED ({str(e)})")
        return False

def create_crawl_job():
    """Create a new crawl job"""
    job_data = {
        "domain": "https://americanspecialties.com/all-washroom-accessories/",
        "manufacturer_name": "American Specialties (ASI)",
        "product_lines": [],
        "sharepoint_folder": "/DocSyncAgent/Test/ASI",
        "weekly_recrawl": False
    }
    
    try:
        response = requests.post(f"{API_BASE}/crawl-jobs", json=job_data, timeout=30)
        if response.status_code == 200:
            job = response.json()
            print(f"✓ Created crawl job: {job['id']}")
            return job
        else:
            print(f"❌ Failed to create crawl job: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating crawl job: {str(e)}")
        return None

def get_crawl_job(job_id):
    """Get crawl job details"""
    try:
        response = requests.get(f"{API_BASE}/crawl-jobs/{job_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get crawl job {job_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting crawl job {job_id}: {str(e)}")
        return None

def get_job_pdfs(job_id):
    """Get PDFs for a crawl job"""
    try:
        response = requests.get(f"{API_BASE}/crawl-jobs/{job_id}/pdfs", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get PDFs for job {job_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting PDFs for job {job_id}: {str(e)}")
        return None

def get_stats():
    """Get API stats"""
    try:
        response = requests.get(f"{API_BASE}/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get stats: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting stats: {str(e)}")
        return None

def cancel_crawl_job(job_id):
    """Cancel a crawl job"""
    try:
        response = requests.post(f"{API_BASE}/crawl-jobs/{job_id}/cancel", timeout=10)
        if response.status_code == 200:
            print(f"✓ Cancelled crawl job {job_id}")
            return True
        else:
            print(f"❌ Failed to cancel crawl job {job_id}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error cancelling crawl job {job_id}: {str(e)}")
        return False

def monitor_existing_job():
    """Monitor the existing crawl job"""
    print("=== Monitoring Existing ASI Crawl Job ===")
    
    # Check if there's an active job
    try:
        response = requests.get(f"{API_BASE}/active-jobs", timeout=10)
        if response.status_code != 200:
            print("❌ Could not get active jobs")
            return False
        
        active_jobs = response.json()
        asi_jobs = [job for job in active_jobs if "American Specialties" in job.get('manufacturer_name', '')]
        
        if not asi_jobs:
            print("No active ASI jobs found")
            return False
        
        job = asi_jobs[0]  # Use the first ASI job
        job_id = job['id']
        print(f"Found active ASI job: {job_id}")
        
        # Monitor for up to 5 minutes
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < 300:  # 5 minutes
            # Check API responsiveness
            stats = get_stats()
            if stats is None:
                print("❌ API became unresponsive")
                return False
            
            # Get job status
            current_job = get_crawl_job(job_id)
            if current_job is None:
                print("❌ Could not retrieve job")
                return False
            
            status = current_job.get('status')
            pdfs_found = current_job.get('total_pdfs_found', 0)
            
            if status != last_status:
                print(f"Job status: {status} (PDFs found: {pdfs_found})")
                last_status = status
            
            # If job completed or failed
            if status in ['completed', 'failed', 'cancelled']:
                print(f"Job finished with status: {status}")
                return analyze_job_results(job_id, current_job)
            
            # If we have PDFs and reached classifying, analyze results
            if status == 'classifying' and pdfs_found > 0:
                print(f"Job reached classifying with {pdfs_found} PDFs - analyzing results")
                time.sleep(30)  # Wait a bit more for classification
                final_job = get_crawl_job(job_id)
                return analyze_job_results(job_id, final_job or current_job)
            
            time.sleep(3)  # Poll every 3 seconds
        
        print("⚠️ Monitoring timeout reached")
        final_job = get_crawl_job(job_id)
        return analyze_job_results(job_id, final_job)
        
    except Exception as e:
        print(f"❌ Error monitoring job: {str(e)}")
        return False

def analyze_job_results(job_id, job):
    """Analyze the results of a crawl job"""
    print(f"\n=== Analyzing Job Results for {job_id} ===")
    
    total_pdfs = job.get('total_pdfs_found', 0)
    print(f"Total PDFs found: {total_pdfs}")
    
    if total_pdfs == 0:
        print("❌ No PDFs were found during crawl")
        return False
    
    # Get PDF details
    pdfs = get_job_pdfs(job_id)
    if not pdfs:
        print("❌ Could not retrieve PDF records")
        return False
    
    print(f"Retrieved {len(pdfs)} PDF records")
    
    # Analyze document types
    expected_types = ["Product Data Sheet", "Specification Sheet", "Submittal Sheet", "Technical Data Sheet"]
    found_types = set()
    installation_manuals_uploaded = 0
    technical_count = 0
    
    for pdf in pdfs:
        doc_type = pdf.get('document_type')
        if doc_type:
            found_types.add(doc_type)
        
        if pdf.get('is_technical'):
            technical_count += 1
        
        # Check Installation Manuals are not uploaded
        if doc_type == "Installation Manual" and pdf.get('sharepoint_uploaded', False):
            installation_manuals_uploaded += 1
    
    print(f"Document types found: {list(found_types)}")
    print(f"Technical PDFs: {technical_count}")
    
    # Check for expected document types
    expected_found = [t for t in expected_types if t in found_types]
    
    success = True
    
    if not expected_found:
        print(f"❌ No expected document types found. Expected: {expected_types}")
        success = False
    else:
        print(f"✓ Found expected document types: {expected_found}")
    
    if installation_manuals_uploaded > 0:
        print(f"❌ {installation_manuals_uploaded} Installation Manuals were uploaded (should be 0)")
        success = False
    else:
        print("✓ Installation Manuals correctly excluded from upload")
    
    return success

def test_cancellation():
    """Test job cancellation"""
    print("\n=== Testing Job Cancellation ===")
    
    # Create a job to cancel
    job = create_crawl_job()
    if not job:
        return False
    
    job_id = job['id']
    
    # Wait a moment for job to start
    time.sleep(5)
    
    # Cancel the job
    if not cancel_crawl_job(job_id):
        return False
    
    # Verify cancellation
    time.sleep(2)
    cancelled_job = get_crawl_job(job_id)
    
    if not cancelled_job:
        print("❌ Could not retrieve cancelled job")
        return False
    
    if cancelled_job.get('status') != 'cancelled':
        print(f"❌ Job status is {cancelled_job.get('status')}, expected 'cancelled'")
        return False
    
    print("✓ Job successfully cancelled")
    return True

def main():
    """Run the tests"""
    print("=== PDF DocSync Agent Backend Tests ===\n")
    
    # Test 1: API Health
    if not test_api_health():
        return False
    
    # Test 2: Monitor existing job or create new one
    job_success = monitor_existing_job()
    
    # Test 3: Cancellation
    cancel_success = test_cancellation()
    
    # Summary
    print(f"\n=== TEST SUMMARY ===")
    print(f"ASI Crawl Test: {'PASSED' if job_success else 'FAILED'}")
    print(f"Cancellation Test: {'PASSED' if cancel_success else 'FAILED'}")
    
    if job_success and cancel_success:
        print("🎉 ALL TESTS PASSED")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)