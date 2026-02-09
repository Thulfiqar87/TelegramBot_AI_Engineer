import asyncio
from src.database import init_db, AsyncSessionLocal
from src.models import ChatLog, ReportCounter
from datetime import datetime

async def test_db():
    print("Initializing DB...")
    await init_db()
    
    print("Creating test chat log...")
    async with AsyncSessionLocal() as session:
        log = ChatLog(
            user_id="12345",
            username="test_user",
            message="Hello DB",
            timestamp=datetime.now()
        )
        session.add(log)
        await session.commit()
        
    print("Reading chat log...")
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(ChatLog).where(ChatLog.username == "test_user"))
        params = result.scalars().first()
        print(f"Retrieved: {params.message}")
        assert params.message == "Hello DB"

    print("Testing Report Counter...")
    async with AsyncSessionLocal() as session:
        counter = ReportCounter(month_key="TEST-KEY", count=0)
        session.add(counter)
        await session.commit()
        
        counter.count += 1
        await session.commit()
        print(f"Counter: {counter.count}")
        assert counter.count == 1

    print("DB Verification Successful.")

if __name__ == "__main__":
    asyncio.run(test_db())
