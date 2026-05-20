"""Current user identity endpoint.

Returns the server-resolved platform role and tenant memberships so the frontend
can render permissions without trusting localStorage or raw Supabase profile reads.
"""

from fastapi import APIRouter, Depends

from app.middleware.security import get_current_user

router = APIRouter()


@router.get("/")
async def get_me(user: dict = Depends(get_current_user)):
    """Return the authenticated user's identity, platform role, and org context."""
    memberships = []
    org_id = user.get("org_id")
    if org_id:
        memberships.append({
            "organization_id": org_id,
            "role": user.get("org_role"),
            "is_owner": bool(user.get("org_owner")),
        })

    return {
        "user_id": user.get("id"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "platform_role": user.get("platform_role", "user"),
        "tier": user.get("tier", "free"),
        "mfa_active": user.get("mfa_active", False),
        "mfa_aal": user.get("mfa_aal", "aal1"),
        "current_org_id": org_id,
        "current_org_role": user.get("org_role"),
        "current_org_owner": bool(user.get("org_owner")),
        "memberships": memberships,
    }
