from supabase import create_client
from dotenv import load_dotenv
import os

def count_ideas():
    load_dotenv("../.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    try:
        client = create_client(url, key)
        
        # 1. Check all ideas
        ideas = client.table('ideas').select('*').execute().data
        print(f"Total ideas in DB: {len(ideas)}")
        
        # 2. Check organizations
        orgs = client.table('organizations').select('*').execute().data
        print(f"Total organizations: {len(orgs)}")
        for org in orgs:
            count = len(client.table('ideas').select('*').eq('organization_id', org['id']).execute().data)
            print(f" - Org: {org['name']} ({org['id']}) has {count} ideas")
            
        # 3. Check for ideas with NULL organization_id
        null_org_ideas = len(client.table('ideas').select('*').is_('organization_id', 'null').execute().data)
        print(f"Ideas with NO organization_id: {null_org_ideas}")

        # 4. Check for current user's ideas
        user_id = 'a9d65f02-efa9-4dc1-a2b2-0d7c6b5516d5'
        user_ideas = len(client.table('ideas').select('*').eq('user_id', user_id).execute().data)
        print(f"Ideas owned by user {user_id}: {user_ideas}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    count_ideas()
