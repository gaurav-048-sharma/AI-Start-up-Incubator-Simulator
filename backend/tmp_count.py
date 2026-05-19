from supabase import create_client
from dotenv import load_dotenv
import os

def check_ideas():
    load_dotenv("../.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    client = create_client(url, key)
    
    ideas = client.table('ideas').select('id').execute().data
    print(f"DEBUG_COUNT={len(ideas)}")

if __name__ == "__main__":
    check_ideas()
