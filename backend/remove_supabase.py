import os

def process_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for old, new in replacements:
        content = content.replace(old, new)
        
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {path}")
    else:
        print(f"No changes in {path}")

websockets_replacements = [
    (
        "from app.models.database import get_supabase_client\n        supabase = get_supabase_client(admin=True)\n        if not supabase:\n            raise ValueError(\"Supabase not configured\")\n        \n        # Verify with Supabase Auth\n        user_response = await _asyncio.to_thread(supabase.auth.get_user, token)\n        if not user_response or not user_response.user:\n            raise ValueError(\"Invalid JWT\")",
        "import jwt\n        from app.config import get_settings\n        settings = get_settings()\n        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[\"HS256\"])\n        user_id = payload.get(\"sub\")\n        if not user_id:\n            raise ValueError(\"Invalid JWT\")\n        # mock user_response\n        class MockUser:\n            pass\n        user_response = MockUser()\n        user_response.user = MockUser()\n        user_response.user.id = user_id\n        user_response.user.email = payload.get(\"email\")"
    ),
    (
        "lambda: supabase.table(\"profiles\")\n                .select(\"company_name, role, tier\")\n                .eq(\"id\", user_response.user.id)\n                .single()\n                .execute()",
        "lambda: None"
    ),
    (
        "profile_data = profile_res.data if hasattr(profile_res, 'data') else None",
        "from app.models.database import get_db_service\n            db = get_db_service()\n            profile_data = await db.get_profile(user_response.user.id)"
    ),
    (
        "from app.models.database import get_supabase_client\n        supabase = get_supabase_client(admin=True)\n        if not supabase:\n            return False\n        \n        # 1. Check if user owns the idea\n        idea_res = await _asyncio.to_thread(\n            lambda: supabase.table(\"ideas\")\n            .select(\"user_id, organization_id\")\n            .eq(\"id\", idea_id)\n            .single()\n            .execute()\n        )",
        "from app.models.database import get_db_service\n        db = get_db_service()\n        idea_data = await db.get_idea(idea_id)\n        if not idea_data:\n            return False\n        class MockRes:\n            data = idea_data\n        idea_res = MockRes()"
    ),
    (
        "org_res = await _asyncio.to_thread(\n                lambda: supabase.table(\"organization_members\")\n                .select(\"id\")\n                .eq(\"organization_id\", idea.get(\"organization_id\"))\n                .eq(\"user_id\", user_id)\n                .single()\n                .execute()\n            )",
        "org_res = None # No orgs in sqlite yet"
    )
]

process_file("app/api/websockets.py", websockets_replacements)

enterprise_replacements = [
    ("from app.models.database import get_supabase_client\n", ""),
    ("admin_client = get_supabase_client(admin=True)\n", "admin_client = None\n"),
    ("if admin_client:", "if False:"),
]
process_file("app/api/routes/enterprise.py", enterprise_replacements)
process_file("app/api/routes/organizations.py", enterprise_replacements)

mfa_replacements = [
    ("settings.supabase_url", "''"),
    ("settings.supabase_anon_key", "''"),
    ("admin_client = get_supabase_client(admin=True)\n", "admin_client = None\n"),
]
process_file("app/api/routes/mfa.py", mfa_replacements)

