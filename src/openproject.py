import aiohttp
import base64
import logging
import json
from urllib.parse import urlparse, quote
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config import Config
from src.schemas import ProjectSummary, WorkPackage

logger = logging.getLogger(__name__)

class OpenProjectClient:
    def __init__(self):
        self.original_url = Config.OPENPROJECT_URL
        self.api_key = Config.OPENPROJECT_API_KEY
        
        # Parse URL to extract project identifier if present
        parsed = urlparse(self.original_url)
        path_parts = parsed.path.strip("/").split("/")
        
        self.project_identifier = None
        # Check if URL ends with /projects/{identifier}
        if "projects" in path_parts:
            try:
                idx = path_parts.index("projects")
                if len(path_parts) > idx + 1:
                    self.project_identifier = path_parts[idx + 1]
            except ValueError:
                pass
        
        # Base URL should be the root (scheme + netloc)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        self.headers = {
            "Authorization": f"Basic {base64.b64encode(f'apikey:{self.api_key}'.encode()).decode()}",
            "Content-Type": "application/json"
        }
        self.project_id = None # Cache for project ID

    async def _get_project_id(self):
        """Resolves project identifier to ID."""
        if not self.project_identifier:
            return None
        if self.project_id:
            return self.project_id
            
        try:
            # Fetch all projects and filter in-memory (API filter 'identifier' was returning 400)
            url = f"{self.base_url}/api/v3/projects"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        elements = data.get("_embedded", {}).get("elements", [])
                        
                        for project in elements:
                            if project.get("identifier") == self.project_identifier:
                                self.project_id = project.get("id")
                                logger.info(f"Resolved project '{self.project_identifier}' to ID {self.project_id}")
                                return self.project_id
                                
            logger.warning(f"Could not resolve project identifier '{self.project_identifier}'")
        except Exception as e:
            logger.error(f"Error resolving project ID: {e}")
        return None


    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_work_packages(self):
        """Fetches work packages from OpenProject with retry logic."""
        try:
            url = f"{self.base_url}/api/v3/work_packages"
            
            # Add project filter if applicable
            project_id = await self._get_project_id()
            if project_id:
                filters = [{"project": {"operator": "=", "values": [str(project_id)]}}]
                url += f"?filters={quote(json.dumps(filters))}"
                
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
