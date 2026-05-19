from supabase import create_client
from dotenv import load_dotenv
import os

def check_admin_data():
    load_dotenv("../.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    try:
        client = create_client(url, key)
        
        reqs = client.table('enterprise_requests').select('*').execute().data
        print(f"Enterprise Requests: {len(reqs)}")
        
        orgs = client.table('organizations').select('*').execute().data
        print(f"Total Organizations: {len(orgs)}")
        
        profiles = client.table('profiles').select('*').execute().data
        print(f"Total Profiles: {len(profiles)}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_admin_data()
