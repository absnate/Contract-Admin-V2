import asyncio
import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from .crawler_service import CrawlerService

logger = logging.getLogger(__name__)


def run_crawl_job_process(
    job_id: str,
    domain: str,
    product_lines: list,
    manufacturer_name: str,
    sharepoint_folder: str,
):
    """Entry point for running a crawl job in a separate OS process."""

    # Ensure env vars (MONGO_URL/DB_NAME/Azure creds/EMERGENT_LLM_KEY) are loaded in child process
    # Also ensure Playwright browser path is set in the child process.
    try:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    except Exception:
        # Env should already be inherited; dotenv load is best-effort
        pass

    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/pw-browsers')

    # Create a new process group so the parent can kill the whole tree (Chromium children, etc.)
    try:
        os.setsid()
    except Exception:
        pass

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        raise RuntimeError("MONGO_URL/DB_NAME not set")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    crawler_service = CrawlerService(db)

    try:
        asyncio.run(
            crawler_service.start_crawl(
                job_id=job_id,
                domain=domain,
                product_lines=product_lines or [],
                manufacturer_name=manufacturer_name,
                sharepoint_folder=sharepoint_folder,
            )
        )
    finally:
        try:
            client.close()
        except Exception:
            pass
