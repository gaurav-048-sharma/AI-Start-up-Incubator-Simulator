import asyncio
from app.models.database import get_db_service

async def test():
    db = get_db_service()
    try:
        profile = await db.get_profile('test')
        print("Profile:", profile)
    except Exception as e:
        print("Error getting profile:", e)

asyncio.run(test())
