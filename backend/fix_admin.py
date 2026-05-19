from dotenv import load_dotenv
import os
import sys
import asyncio

# LOAD THE ENV EXPLICITLY FIRST
load_dotenv(".env")
print(f"🌍 DB URL CHECK: {os.getenv('SUPABASE_URL')[:15]}...")

# Add project root to path
sys.path.append(os.getcwd())

from app.models.database import get_supabase_client

async def fix():
    print("🚀 Identity Correction Engine Starting...")
    client = get_supabase_client(admin=True)
    
    print("🛡️ Patching all profiles to Super Admin...")
    try:
        res = client.table("profiles").update({
            "platform_role": "super_admin",
            "tier": "enterprise"
        }).neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"✅ Success! Updated {len(res.data)} profiles.")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(fix())
