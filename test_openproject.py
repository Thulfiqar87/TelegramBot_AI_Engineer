import asyncio
import logging
from src.openproject import OpenProjectClient
from src.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_openproject():
    print("Testing OpenProject API...")
    try:
        Config.validate()
    except Exception as e:
        print(f"Config validation failed: {e}")
        return

    client = OpenProjectClient()
    
    print("Fetching Summary...")
    try:
        summary = await client.get_summary()
        print(f"Active Packages: {len(summary['active'])}")
        for p in summary['active']:
            print(f" - {p['subject']} ({p['status']})")
            
        print(f"Incoming Packages: {len(summary['incoming'])}")
        for p in summary['incoming']:
            print(f" - {p['subject']} (Start: {p['startDate']})")
            
    except Exception as e:
        print(f"API Call failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_openproject())
