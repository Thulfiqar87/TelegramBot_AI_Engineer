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
        # Parse Base URL matching app logic
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        print(f"Base URL resolved to: {base_url}")
        
        targets = [base_url, "http://127.0.0.1:8080", "http://localhost:8080"]
        success = False
        
        async with aiohttp.ClientSession() as session:
            for target in targets:
                print(f"\nChecking {target}...")
                try:
                    async with session.get(target, timeout=5) as response:
                        print(f"SUCCESS connecting to {target} (Status: {response.status})")
                        success = True
                        
                        # Use this successful base_url for API check
                        api_url = f"{target}/api/v3/projects"
                        print(f"Checking API at {api_url}...")
                        
                        headers = {}
                        if api_key:
                            import base64
                            headers["Authorization"] = f"Basic {base64.b64encode(f'apikey:{api_key}'.encode()).decode()}"
                            
                        async with session.get(api_url, headers=headers, timeout=10) as apiresp:
                            print(f"API Status: {apiresp.status}")
                            if apiresp.status == 200:
                                data = await apiresp.json()
                                projects = data.get("_embedded", {}).get("elements", [])
                                print(f"Projects found: {len(projects)}")
                                for p in projects:
                                    print(f" - {p.get('name')} (ID: {p.get('id')})")
                            else:
                                print(f"API Error. Status: {apiresp.status}")
                        break # Stop after success
                        
                except Exception as e:
                    print(f"Failed to connect to {target}: {e}")
            
            if not success:
               print("\nCRITICAL: Could not connect to OpenProject on any attempted address.")
               print("Suggestions:")
               print("1. Check if OpenProject container is running: 'docker ps'")
               print("2. Check if it's listening on port 8080")
               print("3. Try 'curl -v http://localhost:8080' from the server terminal")

    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_connection())
