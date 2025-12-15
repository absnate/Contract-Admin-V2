from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
import os
import logging
import uuid
import tempfile

# Import services
from services.crawler_service import CrawlerService
from services.pdf_classifier import PDFClassifier
from services.sharepoint_service import SharePointService
from services.scheduler_service import SchedulerService
from services.bulk_upload_service import BulkUploadService
from services.process_runner import run_crawl_job_process

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize services
crawler_service = CrawlerService(db)
pdf_classifier = PDFClassifier()
sharepoint_service = SharePointService()
scheduler_service = SchedulerService(db, crawler_service, pdf_classifier, sharepoint_service)
bulk_upload_service = BulkUploadService(db)

# Create the main app
app = FastAPI(title="PDF DocSync Agent")
api_router = APIRouter(prefix="/api")

# Models
class CrawlJobCreate(BaseModel):
    manufacturer_name: str
    domain: str
    product_lines: Optional[List[str]] = []
    sharepoint_folder: str
    weekly_recrawl: bool = False

class CrawlJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    manufacturer_name: str
    domain: str
    product_lines: List[str]
    sharepoint_folder: str
    weekly_recrawl: bool
    status: str = "pending"  # pending, crawling, classifying, uploading, completed, failed
    total_pdfs_found: int = 0
    total_pdfs_classified: int = 0
    total_pdfs_uploaded: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None

class PDFRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    filename: str
    source_url: str
    file_size: int
    is_technical: bool
    classification_reason: str
    document_type: Optional[str] = None
    sharepoint_uploaded: bool = False
    sharepoint_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Schedule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    manufacturer_name: str
    domain: str
    cron_expression: str = "0 0 * * 0"  # Weekly on Sunday at midnight
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BulkUploadJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    manufacturer_name: str
    sharepoint_folder: str
    status: str = "pending"  # pending, processing, downloading, uploading, completed, failed
    total_items: int = 0
    total_classified: int = 0
    total_uploaded: int = 0
    total_failed: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None

class BulkUploadPDF(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    part_number: str
    filename: str
    source_url: str
    file_size: int
    is_technical: bool
    classification_reason: str
    document_type: Optional[str] = None
    sharepoint_uploaded: bool = False
    sharepoint_id: Optional[str] = None
    download_status: str = "success"  # success, failed
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Routes
@api_router.get("/")
async def root():
    return {"message": "PDF DocSync Agent API", "status": "running"}

@api_router.post("/crawl-jobs", response_model=CrawlJob)
async def create_crawl_job(job_data: CrawlJobCreate, background_tasks: BackgroundTasks):
    """Create a new crawl job"""
    job = CrawlJob(**job_data.model_dump())
    
    # Save to database
    doc = job.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.crawl_jobs.insert_one(doc)
    
    # Start crawling in background
    background_tasks.add_task(
        crawler_service.start_crawl,
        job.id,
        job.domain,
        job.product_lines,
        job.manufacturer_name,
        job.sharepoint_folder
    )
    
    # Schedule weekly recrawl if enabled
    if job.weekly_recrawl:
        schedule = Schedule(job_id=job.id, manufacturer_name=job.manufacturer_name, domain=job.domain)
        schedule_doc = schedule.model_dump()
        schedule_doc['created_at'] = schedule_doc['created_at'].isoformat()
        if schedule_doc.get('last_run'):
            schedule_doc['last_run'] = schedule_doc['last_run'].isoformat()
        if schedule_doc.get('next_run'):
            schedule_doc['next_run'] = schedule_doc['next_run'].isoformat()
        await db.schedules.insert_one(schedule_doc)
        await scheduler_service.schedule_job(job.id, job.domain, job.product_lines, job.manufacturer_name, job.sharepoint_folder)
    
    return job

@api_router.get("/crawl-jobs", response_model=List[CrawlJob])
async def get_crawl_jobs():
    """Get all crawl jobs"""
    jobs = await db.crawl_jobs.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    for job in jobs:
        if isinstance(job.get('created_at'), str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        if isinstance(job.get('updated_at'), str):
            job['updated_at'] = datetime.fromisoformat(job['updated_at'])
    
    return jobs

@api_router.get("/crawl-jobs/{job_id}", response_model=CrawlJob)
async def get_crawl_job(job_id: str):
    """Get a specific crawl job"""
    job = await db.crawl_jobs.find_one({"id": job_id}, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if isinstance(job.get('created_at'), str):
        job['created_at'] = datetime.fromisoformat(job['created_at'])
    if isinstance(job.get('updated_at'), str):
        job['updated_at'] = datetime.fromisoformat(job['updated_at'])
    
    return job

@api_router.get("/crawl-jobs/{job_id}/pdfs", response_model=List[PDFRecord])
async def get_job_pdfs(job_id: str):
    """Get all PDFs for a specific job"""
    pdfs = await db.pdf_records.find({"job_id": job_id}, {"_id": 0}).to_list(1000)
    
    for pdf in pdfs:
        if isinstance(pdf.get('created_at'), str):
            pdf['created_at'] = datetime.fromisoformat(pdf['created_at'])
    
    return pdfs

@api_router.get("/schedules", response_model=List[Schedule])
async def get_schedules():
    """Get all schedules"""
    schedules = await db.schedules.find({}, {"_id": 0}).to_list(1000)
    
    for schedule in schedules:
        if isinstance(schedule.get('created_at'), str):
            schedule['created_at'] = datetime.fromisoformat(schedule['created_at'])
        if isinstance(schedule.get('last_run'), str):
            schedule['last_run'] = datetime.fromisoformat(schedule['last_run'])
        if isinstance(schedule.get('next_run'), str):
            schedule['next_run'] = datetime.fromisoformat(schedule['next_run'])
    
    return schedules

@api_router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Delete a schedule"""
    result = await db.schedules.delete_one({"id": schedule_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    await scheduler_service.remove_job(schedule_id)
    
    return {"message": "Schedule deleted successfully"}

@api_router.post("/crawl-jobs/{job_id}/cancel")
async def cancel_crawl_job(job_id: str):
    """Cancel a running crawl job"""
    job = await db.crawl_jobs.find_one({"id": job_id}, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Only allow cancelling jobs that are in progress
    if job['status'] not in ['pending', 'crawling', 'classifying', 'uploading']:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job['status']}")
    
    # Update job status to cancelled
    await db.crawl_jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "error_message": "Job cancelled by user"
        }}
    )
    
    return {"message": "Job cancelled successfully"}

@api_router.post("/bulk-upload-jobs/{job_id}/cancel")
async def cancel_bulk_upload_job(job_id: str):
    """Cancel a running bulk upload job"""
    job = await db.bulk_upload_jobs.find_one({"id": job_id}, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Only allow cancelling jobs that are in progress
    if job['status'] not in ['pending', 'processing', 'downloading', 'uploading']:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job['status']}")
    
    # Update job status to cancelled
    await db.bulk_upload_jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "error_message": "Job cancelled by user"
        }}
    )
    
    return {"message": "Job cancelled successfully"}

@api_router.get("/active-jobs")
async def get_active_jobs():
    """Get all active (in-progress) jobs"""
    # Get active crawl jobs
    crawl_jobs = await db.crawl_jobs.find({
        "status": {"$in": ["pending", "crawling", "classifying", "uploading"]}
    }, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for job in crawl_jobs:
        if isinstance(job.get('created_at'), str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        if isinstance(job.get('updated_at'), str):
            job['updated_at'] = datetime.fromisoformat(job['updated_at'])
        job['job_type'] = 'crawl'
    
    # Get active bulk upload jobs
    bulk_jobs = await db.bulk_upload_jobs.find({
        "status": {"$in": ["pending", "processing", "downloading", "uploading"]}
    }, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for job in bulk_jobs:
        if isinstance(job.get('created_at'), str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        if isinstance(job.get('updated_at'), str):
            job['updated_at'] = datetime.fromisoformat(job['updated_at'])
        job['job_type'] = 'bulk_upload'
    
    # Combine and sort by created_at
    all_jobs = crawl_jobs + bulk_jobs
    all_jobs.sort(key=lambda x: x['created_at'], reverse=True)
    
    return all_jobs

@api_router.post("/bulk-upload", response_model=BulkUploadJob)
async def create_bulk_upload(
    manufacturer_name: str = Query(...),
    sharepoint_folder: str = Query(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Create a bulk upload job from Excel file"""
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")
    
    # Create job
    job = BulkUploadJob(manufacturer_name=manufacturer_name, sharepoint_folder=sharepoint_folder)
    
    # Save job to database
    doc = job.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.bulk_upload_jobs.insert_one(doc)
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    # Start processing in background
    background_tasks.add_task(
        bulk_upload_service.process_excel_file,
        job.id,
        tmp_path,
        manufacturer_name,
        sharepoint_folder
    )
    
    return job

@api_router.get("/bulk-upload-jobs", response_model=List[BulkUploadJob])
async def get_bulk_upload_jobs():
    """Get all bulk upload jobs"""
    jobs = await db.bulk_upload_jobs.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    for job in jobs:
        if isinstance(job.get('created_at'), str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        if isinstance(job.get('updated_at'), str):
            job['updated_at'] = datetime.fromisoformat(job['updated_at'])
    
    return jobs

@api_router.get("/bulk-upload-jobs/{job_id}", response_model=BulkUploadJob)
async def get_bulk_upload_job(job_id: str):
    """Get a specific bulk upload job"""
    job = await db.bulk_upload_jobs.find_one({"id": job_id}, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if isinstance(job.get('created_at'), str):
        job['created_at'] = datetime.fromisoformat(job['created_at'])
    if isinstance(job.get('updated_at'), str):
        job['updated_at'] = datetime.fromisoformat(job['updated_at'])
    
    return job

@api_router.get("/bulk-upload-jobs/{job_id}/pdfs", response_model=List[BulkUploadPDF])
async def get_bulk_upload_pdfs(job_id: str):
    """Get all PDFs for a specific bulk upload job"""
    pdfs = await db.bulk_upload_pdfs.find({"job_id": job_id}, {"_id": 0}).to_list(1000)
    
    for pdf in pdfs:
        if isinstance(pdf.get('created_at'), str):
            pdf['created_at'] = datetime.fromisoformat(pdf['created_at'])
    
    return pdfs

@api_router.get("/stats")
async def get_stats():
    """Get dashboard statistics"""
    total_jobs = await db.crawl_jobs.count_documents({})
    active_crawl_jobs = await db.crawl_jobs.count_documents({"status": {"$in": ["pending", "crawling", "classifying", "uploading"]}})
    total_pdfs = await db.pdf_records.count_documents({})
    technical_pdfs = await db.pdf_records.count_documents({"is_technical": True})
    uploaded_pdfs = await db.pdf_records.count_documents({"sharepoint_uploaded": True})
    active_schedules = await db.schedules.count_documents({"enabled": True})
    
    # Bulk upload stats
    bulk_jobs = await db.bulk_upload_jobs.count_documents({})
    active_bulk_jobs = await db.bulk_upload_jobs.count_documents({"status": {"$in": ["pending", "processing", "downloading", "uploading"]}})
    bulk_pdfs = await db.bulk_upload_pdfs.count_documents({})
    bulk_technical = await db.bulk_upload_pdfs.count_documents({"is_technical": True})
    bulk_uploaded = await db.bulk_upload_pdfs.count_documents({"sharepoint_uploaded": True})
    
    # Combined active jobs count
    total_active_jobs = active_crawl_jobs + active_bulk_jobs
    
    return {
        "total_jobs": total_jobs,
        "active_jobs": total_active_jobs,
        "total_pdfs": total_pdfs,
        "technical_pdfs": technical_pdfs,
        "uploaded_pdfs": uploaded_pdfs,
        "active_schedules": active_schedules,
        "bulk_jobs": bulk_jobs,
        "bulk_pdfs": bulk_pdfs,
        "bulk_technical": bulk_technical,
        "bulk_uploaded": bulk_uploaded
    }

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup():
    logger.info("Starting PDF DocSync Agent...")
    # Initialize scheduler
    await scheduler_service.start()
    logger.info("Scheduler started")

@app.on_event("shutdown")
async def shutdown_db_client():
    await scheduler_service.shutdown()
    client.close()
    logger.info("Application shutdown complete")