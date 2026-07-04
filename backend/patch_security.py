import re
import os

with open("app/middleware/security.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the supabase.auth.get_user part
old_auth_code = """        # Use the admin client to get user details
        try:
            user_response = await asyncio.to_thread(supabase.auth.get_user, credentials.credentials)
        except Exception as auth_err:
            logger.error("Supabase auth.get_user failed", error=str(auth_err))
            raise HTTPException(status_code=401, detail=f"Invalid or expired session: {str(auth_err)}")

        if not user_response or not user_response.user:
            logger.warning("No user found in Supabase session")
            raise HTTPException(status_code=401, detail="User session not found or has been revoked")

        user = user_response.user
        user_id = str(user.id)

        # user_metadata/app_metadata can be arbitrary JSON values; coerce to dict for safe .get() usage
        raw_user_meta = getattr(user, "user_metadata", None) or {}
        user_meta = raw_user_meta if isinstance(raw_user_meta, dict) else {}
        user_tier = user_meta.get("tier", "free")

        # MFA Context: Authenticator Assurance Level (aal1 = password, aal2 = MFA)
        raw_app_meta = getattr(user, "app_metadata", None) or {}
        auth_app_metadata = raw_app_meta if isinstance(raw_app_meta, dict) else {}
        aal = auth_app_metadata.get("aal", "aal1")"""

new_auth_code = """        # Use the admin client to get user details via AsyncClient to prevent WinError 10035 socket exhaustion
        import httpx
        from app.models.database import _shared_httpx_client
        import app.models.database as db_module

        if getattr(db_module, "_shared_httpx_client", None) is None:
            db_module._shared_httpx_client = httpx.AsyncClient(timeout=10.0)
        
        async_client = db_module._shared_httpx_client

        try:
            auth_resp = await async_client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {credentials.credentials}",
                    "apikey": settings.supabase_anon_key
                }
            )
            if auth_resp.status_code != 200:
                raise Exception(auth_resp.text)
            user_data = auth_resp.json()
        except Exception as auth_err:
            logger.error("Supabase auth API failed", error=str(auth_err))
            raise HTTPException(status_code=401, detail=f"Invalid or expired session")

        if not user_data or "id" not in user_data:
            logger.warning("No user found in Supabase session")
            raise HTTPException(status_code=401, detail="User session not found or has been revoked")

        user_id = str(user_data["id"])

        # user_metadata/app_metadata can be arbitrary JSON values; coerce to dict for safe .get() usage
        raw_user_meta = user_data.get("user_metadata", {})
        user_meta = raw_user_meta if isinstance(raw_user_meta, dict) else {}
        user_tier = user_meta.get("tier", "free")

        # MFA Context: Authenticator Assurance Level (aal1 = password, aal2 = MFA)
        raw_app_meta = user_data.get("app_metadata", {})
        auth_app_metadata = raw_app_meta if isinstance(raw_app_meta, dict) else {}
        aal = auth_app_metadata.get("aal", "aal1")"""

content = content.replace(old_auth_code, new_auth_code)

old_profile_code = """                db_client = get_supabase_client(admin=True)
                profile = await asyncio.to_thread(
                    lambda: db_client.table("profiles")
                    .select("platform_role, role, tier")
                    .eq("id", user_id)
                    .single()
                    .execute()
                )
                if profile.data and isinstance(profile.data, dict):
                    platform_role = profile.data.get("platform_role") or platform_role
                    profile_role = profile.data.get("role") or profile_role
                    user_tier = profile.data.get("tier") or user_tier"""

new_profile_code = """                # Fetch profile using async httpx directly to avoid thread issues
                prof_resp = await async_client.get(
                    f"{settings.supabase_url}/rest/v1/profiles",
                    params={"id": f"eq.{user_id}", "select": "platform_role, role, tier"},
                    headers={
                        "Authorization": f"Bearer {settings.supabase_service_role_key}",
                        "apikey": settings.supabase_anon_key,
                        "Accept": "application/json"
                    }
                )
                if prof_resp.status_code == 200:
                    prof_data = prof_resp.json()
                    if prof_data and len(prof_data) > 0:
                        profile_dict = prof_data[0]
                        platform_role = profile_dict.get("platform_role") or platform_role
                        profile_role = profile_dict.get("role") or profile_role
                        user_tier = profile_dict.get("tier") or user_tier"""

content = content.replace(old_profile_code, new_profile_code)

# Replace org_details code as well to prevent any more asyncio.to_thread issues in get_current_user
old_org_code = """                # Fetch org details + membership in a single pass where possible
                org_details = await asyncio.to_thread(
                    lambda: supabase.table("organizations")
                    .select("owner_id, status, subscription_status")
                    .eq("id", org_id)
                    .single()
                    .execute()
                )

                # ── Org status enforcement ──────────────────────────
                if org_details.data and isinstance(org_details.data, dict):
                    org_status = org_details.data.get("status", "active")
                    sub_status = org_details.data.get("subscription_status", "active")"""

new_org_code = """                # Fetch org details + membership in a single pass where possible
                org_resp = await async_client.get(
                    f"{settings.supabase_url}/rest/v1/organizations",
                    params={"id": f"eq.{org_id}", "select": "owner_id, status, subscription_status"},
                    headers={
                        "Authorization": f"Bearer {settings.supabase_service_role_key}",
                        "apikey": settings.supabase_anon_key,
                        "Accept": "application/json"
                    }
                )

                org_data = org_resp.json()[0] if org_resp.status_code == 200 and len(org_resp.json()) > 0 else None

                # ── Org status enforcement ──────────────────────────
                if org_data:
                    org_status = org_data.get("status", "active")
                    sub_status = org_data.get("subscription_status", "active")"""

content = content.replace(old_org_code, new_org_code)
content = content.replace("owner_id = org_details.data.get(\"owner_id\")", "owner_id = org_data.get(\"owner_id\")")

old_membership_code = """                membership = await asyncio.to_thread(
                    lambda: supabase.table("organization_members")
                    .select("role")
                    .eq("organization_id", org_id)
                    .eq("user_id", user_id)
                    .single()
                    .execute()
                )
                if membership.data and isinstance(membership.data, dict):
                    org_role = membership.data.get("role")
                else:"""

new_membership_code = """                mem_resp = await async_client.get(
                    f"{settings.supabase_url}/rest/v1/organization_members",
                    params={"organization_id": f"eq.{org_id}", "user_id": f"eq.{user_id}", "select": "role"},
                    headers={
                        "Authorization": f"Bearer {settings.supabase_service_role_key}",
                        "apikey": settings.supabase_anon_key,
                        "Accept": "application/json"
                    }
                )
                mem_data = mem_resp.json()[0] if mem_resp.status_code == 200 and len(mem_resp.json()) > 0 else None
                if mem_data:
                    org_role = mem_data.get("role")
                else:"""
content = content.replace(old_membership_code, new_membership_code)

with open("app/middleware/security.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Done patching security.py")
