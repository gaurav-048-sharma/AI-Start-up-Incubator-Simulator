import asyncio
from app.config import get_settings
from app.models.database import DatabaseService, get_supabase_client

async def test_supabase():
    settings = get_settings()
    print(f"Has Supabase Configured? {settings.has_supabase}")
    if not settings.has_supabase:
        print("Supabase is NOT configured in .env!")
        return

    client = get_supabase_client(admin=True)
    if not client:
        print("Failed to get Supabase client!")
        return

    try:
        response = client.table("profiles").select("count", count="exact").execute()
        print(f"Successfully connected to Supabase! Found {response.count} profiles in the DB.")
    except Exception as e:
        print(f"Error querying Supabase: {e}")

if __name__ == "__main__":
    asyncio.run(test_supabase())
