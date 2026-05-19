from supabase import create_client
from dotenv import load_dotenv
import os

def check_rls():
    load_dotenv("../.env")
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    print("Testing with ANON KEY (no JWT)...")
    try:
        client = create_client(url, anon_key)
        data = client.table('ideas').select('id').limit(1).execute().data
        print(f"Anon (no JWT) result: {len(data)} rows")
    except Exception as e:
        print(f"Anon (no JWT) error: {str(e)}")

    print("\nTesting with SERVICE KEY...")
    try:
        client = create_client(url, service_key)
        data = client.table('ideas').select('id').limit(1).execute().data
        print(f"Service key result: {len(data)} rows")
    except Exception as e:
        print(f"Service key error: {str(e)}")

if __name__ == "__main__":
    check_rls()
