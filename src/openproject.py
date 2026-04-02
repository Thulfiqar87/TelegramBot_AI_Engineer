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
        """Fetches ALL work packages from OpenProject with retry logic (no pagination limit)."""
        try:
            url = f"{self.base_url}/api/v3/work_packages?pageSize=500"

            # Add project filter if applicable
            project_id = await self._get_project_id()
            if project_id:
                filters = [{"project": {"operator": "=", "values": [str(project_id)]}}]
                url += f"&filters={quote(json.dumps(filters))}"

            async with self._get_session().get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("_embedded", {}).get("elements", [])
        except Exception as e:
            logger.error(f"Error fetching OpenProject data: {e}")
            raise

    async def get_summary(self) -> dict:
        """Returns a cascaded summary of active (In Progress / On Hold) work packages."""
        summary = {"active": []}

        try:
            packages = await self.get_work_packages()
        except Exception:
            return summary

        logger.info(f"Processing {len(packages)} work packages for summary...")

        # Build a full lookup of all packages (for parent resolution)
        all_pkg_map = {pkg.get("id"): pkg for pkg in packages}

        def _make_item(pkg, children=None):
            pkg_id = pkg.get("id")
            status = pkg.get("_links", {}).get("status", {}).get("title", "").strip()
            return {
                "id": pkg_id,
                "subject": pkg.get("subject", ""),
                "status": status,
                "dueDate": pkg.get("dueDate") or "",
                "startDate": pkg.get("startDate") or "",
                "url": f"{self.base_url}/work_packages/{pkg_id}/activity" if pkg_id else "",
                "children": children or []
            }

        def _is_active(pkg):
            status = pkg.get("_links", {}).get("status", {}).get("title", "").lower()
            return "in progress" in status or "on hold" in status

        def _parent_id(pkg):
            href = pkg.get("_links", {}).get("parent", {}).get("href")
            if not href:
                return None
            try:
                return int(href.split("/")[-1])
            except ValueError:
                return None

        # Separate into parents (no parent link) and children
        active_packages = [p for p in packages if _is_active(p)]

        # For each active package, determine if it's a root or has a parent
        # Build result as: active parents (with their active children) + orphaned active children
        active_ids = {p.get("id") for p in active_packages}
        active_map = {p.get("id"): _make_item(p) for p in active_packages}

        top_level = []
        stub_parents = {}  # parent_id -> stub item for inactive parents that have active children

        for pkg in active_packages:
            pid = _parent_id(pkg)
            item = active_map[pkg.get("id")]

            if pid is None:
                # Root-level active package — will collect children later
                top_level.append(item)
            elif pid in active_ids:
                # Parent is itself active — nest under it
                active_map[pid]["children"].append(item)
            else:
                # Parent exists but is not active — create a stub parent for context
                if pid not in stub_parents:
                    parent_pkg = all_pkg_map.get(pid)
                    if parent_pkg:
                        stub = _make_item(parent_pkg)
                        stub["status"] = "مهام فرعية نشطة"
                    else:
                        stub = {
                            "id": pid,
                            "subject": f"مجموعة أعمال {pid}",
                            "status": "مهام فرعية نشطة",
                            "dueDate": "",
                            "startDate": "",
                            "url": f"{self.base_url}/work_packages/{pid}/activity",
                            "children": []
                        }
                    stub_parents[pid] = stub
                stub_parents[pid]["children"].append(item)

        top_level.extend(stub_parents.values())
        top_level.sort(key=lambda x: x["id"])

        # Sort children within each parent by id
        for item in top_level:
            item["children"].sort(key=lambda x: x["id"])

        summary["active"] = top_level
        logger.info(f"Summary: {len(top_level)} top-level groups, "
                    f"{sum(len(i['children']) for i in top_level)} nested children.")
        return dict(summary)
