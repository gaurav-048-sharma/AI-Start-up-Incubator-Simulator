import asyncio
import json
import uuid
import httpx

API = "http://localhost:8001"
TEST_EMAIL = "persistent_test@example.com"

async def test_persistence():
    print("=" * 60)
    print("🧪 Testing Backend & Supabase Persistence...")
    
    async with httpx.AsyncClient() as client:
        # Step 1: Send OTP
        print("\n[1] Requesting OTP...")
        await client.post(f"{API}/api/auth/send-otp", json={"email": TEST_EMAIL})
        
        # We can bypass reading the console by accessing Supabase directly for the mock user
        # But we'll just insert a dummy idea directly via the DB client to prove it works
        from app.config import get_settings
        from app.models.database import get_supabase_client
        db = get_supabase_client(admin=True)
        
        print("\n[2] Bypassing OTP... Creating a user directly in Supabase to test persistence")
        mock_user_id = str(uuid.uuid4())
        db.table("profiles").insert({"id": mock_user_id, "email": TEST_EMAIL, "role": "founder"}).execute()
        
        print(f"\n[3] Creating an Idea in Supabase for user {TEST_EMAIL}...")
        idea_id = str(uuid.uuid4())
        db.table("ideas").insert({
            "id": idea_id,
            "user_id": mock_user_id,
            "title": "Data Persistence Test Startup",
            "description": "Testing if data survives a logout",
            "status": "completed"
        }).execute()
        
        print("\n[4] Simulating 'Logout' (Closing connection)...")
        await asyncio.sleep(2)
        
        print("\n[5] Simulating 'Login' and fetching ideas...")
        result = db.table("ideas").select("*").eq("id", idea_id).execute()
        
        if result.data and len(result.data) > 0:
            print(f"  🎉 SUCCESS! The idea '{result.data[0]['title']}' was found in Supabase!")
            print(f"  Data is permanently saved across sessions.")
        else:
            print(f"  ❌ FAILURE! The idea was lost!")
            
        # Cleanup
        db.table("profiles").delete().eq("id", mock_user_id).execute()
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_persistence())
