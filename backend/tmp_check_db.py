from app.models.database import get_supabase_client
from app.config import get_settings

def check():
    client = get_supabase_client(admin=True)
    res = client.table("enterprise_requests").select("*").execute()
    print(f"Total Requests: {len(res.data)}")
    for r in res.data:
        print(f"- ID: {r['id']}, Status: {r['status']}, Company: {r['company_name']}")

if __name__ == "__main__":
    check()
