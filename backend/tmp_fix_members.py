import os
import uuid
from app.models.database import get_db_service

os.environ["SUPABASE_URL"] = "https://surlsipljwibjyzljtto.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN1cmxzaXBsandpYmp5emxqdHRvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODk1MDIzNiwiZXhwIjoyMDk0NTI2MjM2fQ.e_AuCA8CFML57-V_UKLer7MzAp6KHmaMyaHPXCdMRQY"

db = get_db_service()

# 1. Find user by email
user_email = "rohansharmas028@gmail.com"
# Note: In some setups, profiles might not have email, check auth.users? 
# But let's check profiles first for anyone.
profiles = db._client.table('profiles').select('*').execute()
user_id = None
for p in profiles.data:
    print(f"Found Profile: {p.get('full_name')} (ID: {p['id']})")
    user_id = p['id'] # Just take the first one found for now if it's the only user

# 2. Find ai.org
orgs = db._client.table('organizations').select('id, name').eq('name', 'ai.org').execute()
ai_org_id = orgs.data[0]['id'] if orgs.data else None

# 3. Create membership as incubator_manager
if user_id and ai_org_id:
    print(f"Adding user {user_id} as incubator_manager of {ai_org_id}...")
    db._client.table('organization_members').insert({
        'id': str(uuid.uuid4()),
        'organization_id': ai_org_id,
        'user_id': user_id,
        'role': 'incubator_manager'
    }).execute()
    print("Membership created.")

    # Also add to Tech as admin so they can invite?
    tech_orgs = db._client.table('organizations').select('id, name').eq('name', 'Tech').execute()
    if tech_orgs.data:
        tech_id = tech_orgs.data[0]['id']
        print(f"Adding user {user_id} as admin of Tech ({tech_id})...")
        db._client.table('organization_members').insert({
            'id': str(uuid.uuid4()),
            'organization_id': tech_id,
            'user_id': user_id,
            'role': 'admin'
        }).execute()
        print("Tech Membership created.")
