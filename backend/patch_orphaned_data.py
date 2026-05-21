import os
from dotenv import load_dotenv
from supabase import create_client

def patch_orphaned_ideas():
    # Load from root .env
    load_dotenv("../.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in .env")
        return

    try:
        client = create_client(url, key)
        
        # 1. Get the first organization to use as default
        orgs = client.table('organizations').select('id, name').execute().data
        if not orgs:
            print("No organizations found. Please create an organization first.")
            return
        
        default_org = orgs[0]
        print(f"Using organization '{default_org['name']}' ({default_org['id']}) as default.")

        # 2. Find orphaned ideas (no organization_id)
        orphaned = client.table('ideas').select('id, title').is_('organization_id', 'null').execute().data
        
        if not orphaned:
            print("No orphaned ideas found.")
            return
        
        print(f"Found {len(orphaned)} orphaned ideas.")

        # 3. Patch each orphaned idea
        for idea in orphaned:
            print(f" - Patching idea: {idea['title']} ({idea['id']})")
            client.table('ideas').update({'organization_id': default_org['id']}).eq('id', idea['id']).execute()
            
        # 4. Do the same for reports (if any orphaned)
        orphaned_reports = client.table('reports').select('id').is_('organization_id', 'null').execute().data
        if orphaned_reports:
            print(f"Found {len(orphaned_reports)} orphaned reports. Patching...")
            for report in orphaned_reports:
                client.table('reports').update({'organization_id': default_org['id']}).eq('id', report['id']).execute()

        print("Patch complete! Refresh the dashboard to see your data.")

    except Exception as e:
        print(f"Error during patch: {str(e)}")

if __name__ == "__main__":
    patch_orphaned_ideas()
