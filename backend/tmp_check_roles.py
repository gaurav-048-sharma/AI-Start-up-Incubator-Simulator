import os
from dotenv import load_dotenv
from supabase import create_client

def check_roles():
    load_dotenv("../.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    client = create_client(url, key)
    
    users = client.table('profiles').select('id, full_name, platform_role').execute().data
    print("Platform Users:")
    for u in users:
        print(f" - {u['full_name']} ({u['id']}): {u['platform_role']}")

if __name__ == "__main__":
    check_roles()
