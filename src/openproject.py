import aiohttp
import base64
import logging
import json
from urllib.parse import urlparse, quote
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config import Config

logger = logging.getLogger(__name__)


class OpenProjectClient:
    def __init__(self):
        raw_url = Config.OPENPROJECT_URL

        # Clean up potential copy-paste errors in env var (e.g. OPENPROJECT_URL=http...)
        if raw_url.startswith("OPENPROJECT_URL="):
            raw_url = raw_url.split("=", 1)[1]

        self.original_url = raw_url.strip()
        self.api_key = Config.OPENPROJECT_API_KEY

        # Parse URL
        parsed = urlparse(self.original_url)

        # Extract Identifier from path if present (e.g. /projects/identifier)
        self.project_identifier = None
        path_parts = parsed.path.strip("/").split("/")

        if "projects" in path_parts:
            try:
                idx = path_parts.index("projects")
                if len(path_parts) > idx + 1:
                    self.project_identifier = path_parts[idx + 1]
            except ValueError:
                pass

        # Derive Base URL (Scheme + Netloc only)
        # e.g. http://host/projects/foo -> http://host
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        logger.info(f"OpenProject Config: Base='{self.base_url}', ID='{self.project_identifier}'")

        self.headers = {
            "Authorization": f"Basic {base64.b64encode(f'apikey:{self.api_key}'.encode()).decode()}",
            "Content-Type": "application/json"
        }
        self.project_id = None  # Cache for project ID
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Returns the shared session, creating it if needed."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def close(self):
        """Closes the shared HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_project_id(self):
        """Resolves project identifier to ID."""
        if not self.project_identifier:
            return None
        if self.project_id:
            return self.project_id

        try:
            # Fetch all projects and filter in-memory (API filter 'identifier' was returning 400)
            url = f"{self.base_url}/api/v3/projects"

            async with self._get_session().get(url) as response:
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

            async with self._get_session().get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("_embedded", {}).get("elements", [])
        except Exception as e:
            logger.error(f"Error fetching OpenProject data: {e}")
            raise

    async def get_summary(self) -> dict:
        """Returns a summary of active work packages."""
        summary = {"active": []}

        try:
            packages = await self.get_work_packages()
        except Exception:
            # Fallback to empty if retries fail
            return summary

        logger.info(f"Processing {len(packages)} work packages for summary...")

        for pkg in packages:
            try:
                status = pkg.get("_links", {}).get("status", {}).get("title", "").strip()
                status_lower = status.lower()

                item = {
                    "id": pkg.get("id"),
                    "subject": pkg.get("subject"),
                    "status": status,
                    "dueDate": pkg.get("dueDate"),
                    "startDate": pkg.get("startDate")
                }

                # Case-insensitive substring match for active packages
                if "in progress" in status_lower:
                    summary["active"].append(item)
                    logger.info(f"Added active package: {item['subject']} ({status})")

            except Exception as e:
                logger.warning(f"Error processing package {pkg.get('id')}: {e}")
                continue

        logger.info(f"Summary prepared: {len(summary['active'])} active.")
        return summary
