import os
from app.models.database import get_db_service

os.environ["SUPABASE_URL"] = "https://surlsipljwibjyzljtto.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN1cmxzaXBsandpYmp5emxqdHRvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODk1MDIzNiwiZXhwIjoyMDk0NTI2MjM2fQ.e_AuCA8CFML57-V_UKLer7MzAp6KHmaMyaHPXCdMRQY"

db = get_db_service()
profiles = db._client.table('profiles').select('id, full_name, email').execute()
for p in profiles.data:
    print(f"{p['full_name']} / {p['email']}: {p['id']}")
