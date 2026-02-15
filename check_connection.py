import os
import asyncio
import aiohttp
import sys

# Get URL from env or default
url = os.getenv("OPENPROJECT_URL", "http://192.168.1.8:8080")
api_key = os.getenv("OPENPROJECT_API_KEY")

print(f"--- Diagnostic: Checking OpenProject Connection ---")
print(f"Target URL: {url}")
print(f"API Key Present: {bool(api_key)}")

async def check_connection():
    try:
        async with aiohttp.ClientSession() as session:
            # Check root
            print(f"Attempting to connect to {url}...")
            async with session.get(url, timeout=5) as response:
                print(f"Root Status: {response.status}")
                
            # Check API projects
            api_url = f"{url}/api/v3/projects"
            print(f"Attempting to fetch projects from {api_url}...")
            
            headers = {}
            if api_key:
                import base64
                headers["Authorization"] = f"Basic {base64.b64encode(f'apikey:{api_key}'.encode()).decode()}"
                
            async with session.get(api_url, headers=headers, timeout=10) as response:
                print(f"projects API Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    projects = data.get("_embedded", {}).get("elements", [])
                    print(f"Projects found: {len(projects)}")
                    for p in projects:
                        print(f" - {p.get('name')} (ID: {p.get('id')})")
                else:
                    text = await response.text()
                    print(f"Error Body: {text[:200]}")
                    
    except Exception as e:
        print(f"CONNECTION FAILED: {e}")
        print("Note: If running in Docker without 'network_mode: host', 192.168.1.8 may not be accessible.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_connection())
