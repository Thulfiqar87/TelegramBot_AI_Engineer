import aiohttp
import base64
import logging
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config import Config
from src.schemas import ProjectSummary, WorkPackage

logger = logging.getLogger(__name__)

class OpenProjectClient:
    def __init__(self):
        self.base_url = Config.OPENPROJECT_URL
        self.api_key = Config.OPENPROJECT_API_KEY
        self.headers = {
            "Authorization": f"Basic {base64.b64encode(f'apikey:{self.api_key}'.encode()).decode()}",
            "Content-Type": "application/json"
        }

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_work_packages(self):
        """Fetches work packages from OpenProject with retry logic."""
        try:
            url = f"{self.base_url}/api/v3/work_packages"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get("_embedded", {}).get("elements", [])
        except Exception as e:
            logger.error(f"Error fetching OpenProject data: {e}")
            raise e # Retry will catch this if it fits exception type, otherwise logs and re-raises

    async def get_summary(self) -> dict:
        """Returns a summary of work packages split into active and incoming."""
        summary = {
            "active": [],
            "incoming": []
        }
        
        try:
            packages = await self.get_work_packages()
        except Exception:
            # Fallback to empty if retries fail
            return summary

        today = datetime.now().date()
        
        for pkg in packages:
            try:
                status = pkg.get("_links", {}).get("status", {}).get("title", "").lower()
                start_date_str = pkg.get("startDate")
                due_date_str = pkg.get("dueDate")
                
                # Parse dates
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date() if due_date_str else None

                item = {
                    "id": pkg.get("id"),
                    "subject": pkg.get("subject"),
                    "status": status,
                    "dueDate": due_date_str, # Keep string for template compatibility or update template
                    "startDate": start_date_str
                }
                
                # Logic for Active Only (In Progress)
                if status == "in progress":
                    summary["active"].append(item)
                
                # Incoming logic removed as per user request
                
            except Exception as e:
                logger.warning(f"Error processing package {pkg.get('id')}: {e}")
                continue
                
        return summary
