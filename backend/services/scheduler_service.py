from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, db, crawler_service, pdf_classifier, sharepoint_service):
        self.db = db
        self.crawler_service = crawler_service
        self.pdf_classifier = pdf_classifier
        self.sharepoint_service = sharepoint_service
        self.scheduler = AsyncIOScheduler()
    
    async def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Scheduler started")
        
        # Load existing schedules from database
        await self._load_schedules()
    
    async def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")
    
    async def schedule_job(self, job_id: str, domain: str, product_lines: list, manufacturer_name: str, sharepoint_folder: str):
        """Schedule a weekly recrawl job"""
        try:
            # Schedule for every Sunday at midnight
            self.scheduler.add_job(
                func=self._execute_scheduled_crawl,
                trigger=CronTrigger(day_of_week='sun', hour=0, minute=0),
                args=[job_id, domain, product_lines, manufacturer_name, sharepoint_folder],
                id=f"job_{job_id}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled weekly recrawl for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to schedule job {job_id}: {str(e)}")
    
    async def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(f"job_{job_id}")
            logger.info(f"Removed scheduled job {job_id}")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {str(e)}")
    
    async def _load_schedules(self):
        """Load and schedule all active schedules from database"""
        schedules = await self.db.schedules.find({"enabled": True}).to_list(1000)
        
        for schedule in schedules:
            # Get the original job
            job = await self.db.crawl_jobs.find_one({"id": schedule['job_id']})
            
            if job:
                await self.schedule_job(
                    schedule['job_id'],
                    job['domain'],
                    job['product_lines'],
                    job['manufacturer_name'],
                    job['sharepoint_folder']
                )
        
        logger.info(f"Loaded {len(schedules)} schedules")
    
    async def _execute_scheduled_crawl(self, job_id: str, domain: str, product_lines: list, manufacturer_name: str, sharepoint_folder: str):
        """Execute a scheduled crawl"""
        logger.info(f"Executing scheduled crawl for job {job_id}")
        
        try:
            # Update last run time
            await self.db.schedules.update_one(
                {"job_id": job_id},
                {"$set": {"last_run": datetime.now(timezone.utc).isoformat()}}
            )
            
            # Create a new crawl job instance
            from uuid import uuid4
            new_job_id = str(uuid4())
            
            # Start the crawl
            await self.crawler_service.start_crawl(
                new_job_id,
                domain,
                product_lines,
                manufacturer_name,
                sharepoint_folder
            )
            
            logger.info(f"Scheduled crawl completed for job {job_id}")
        except Exception as e:
            logger.error(f"Scheduled crawl failed for job {job_id}: {str(e)}")