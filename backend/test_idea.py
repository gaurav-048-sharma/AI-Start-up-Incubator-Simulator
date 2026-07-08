import asyncio
import uuid
from app.models.database import get_db_service
from datetime import datetime, timezone

async def test():
    db = get_db_service()
    try:
        res = await db.create_idea({
            "id": str(uuid.uuid4()),
            "user_id": '1bc6e26c-fcd3-45b3-b75d-f7c299af4d9c', # Example user ID that doesn't exist in Supabase auth.users
            "organization_id": None,
            "title": "test title",
            "description": "test description",
            "industry": "test industry",
            "target_market": "test target market",
            "problem_statement": "test problem",
            "proposed_solution": "test solution",
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        print("Result:", res)
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
