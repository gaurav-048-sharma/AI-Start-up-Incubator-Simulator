"""
Organization & Team API Routes — multi-tenant workspace management.
Handles org CRUD, member management, invitations, and audit log.
"""

import uuid
import secrets
import structlog
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

from app.middleware.security import (
    get_current_user,
    require_minimum_role,
    require_permission,
    log_audit_event,
    ROLE_HIERARCHY,
    ROLE_DESCRIPTIONS,
)

logger = structlog.get_logger()
router = APIRouter()


# ── Request/Response Models ──────────────────────────────────────

class OrgCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")

class OrgUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    logo_url: Optional[str] = None
    settings: Optional[dict] = None

class InviteRequest(BaseModel):
    email: str = Field(..., description="Email to invite")
    role: str = Field(default="team_member", description="Role to assign")

class RoleUpdateRequest(BaseModel):
    role: str = Field(..., description="New role to assign")


# ── Roles Info ───────────────────────────────────────────────────

@router.get("/roles")
async def list_roles():
    """List all available roles with descriptions and hierarchy levels."""
    return {
        "roles": [
            {
                "id": role,
                "label": role.replace("_", " ").title(),
                "level": level,
                "description": ROLE_DESCRIPTIONS.get(role, ""),
            }
            for role, level in sorted(ROLE_HIERARCHY.items(), key=lambda x: x[1])
        ]
    }


# ── Organization CRUD ────────────────────────────────────────────

@router.post("")
async def create_org(
    body: OrgCreate,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Create a new organization. The creator becomes the admin."""
    from app.models.database import get_db_service
    db = get_db_service()

    org_id = str(uuid.uuid4())
    try:
        org_data = {
            "id": org_id,
            "name": body.name,
            "slug": body.slug,
            "owner_id": user["id"],
            "plan": user.get("tier", "free"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        result = db._client.table("organizations").insert(org_data).execute()

        # Add creator as admin member
        membership = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": user["id"],
            "role": "admin",
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        db._client.table("organization_members").insert(membership).execute()

        # Set as user's current org
        db._client.table("profiles").update(
            {"current_org_id": org_id}
        ).eq("id", user["id"]).execute()

        await log_audit_event(
            user_id=user["id"],
            action="create_organization",
            resource_type="organization",
            resource_id=org_id,
            org_id=org_id,
            details={"name": body.name, "slug": body.slug},
            request=request,
        )

        return result.data[0] if result.data else org_data
    except Exception as e:
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Organization slug '{body.slug}' already exists")
        logger.error("Failed to create org", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create organization")


@router.get("")
async def list_my_orgs(user: dict = Depends(get_current_user)):
    """List organizations the current user belongs to."""
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        result = (
            db._client.table("organization_members")
            .select("organization_id, role, organizations(id, name, slug, logo_url, plan, owner_id, created_at)")
            .eq("user_id", user["id"])
            .execute()
        )
        return {
            "organizations": [
                {
                    "id": m["organizations"]["id"],
                    "name": m["organizations"]["name"],
                    "slug": m["organizations"]["slug"],
                    "logo_url": m["organizations"]["logo_url"],
                    "plan": m["organizations"]["plan"],
                    "my_role": m["role"],
                    "is_owner": m["organizations"]["owner_id"] == user["id"],
                }
                for m in (result.data or [])
                if m.get("organizations")
            ]
        }
    except Exception as e:
        logger.error("Failed to list orgs", error=str(e))
        return {"organizations": []}


@router.get("/{org_id}")
async def get_org(org_id: str, user: dict = Depends(get_current_user)):
    """Get organization details (members must be in the org)."""
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        org = db._client.table("organizations").select("*").eq("id", org_id).single().execute()
        if not org.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Check membership
        member = (
            db._client.table("organization_members")
            .select("role")
            .eq("organization_id", org_id)
            .eq("user_id", user["id"])
            .single()
            .execute()
        )
        if not member.data:
            raise HTTPException(status_code=403, detail="You are not a member of this organization")

        # Get member count
        members = (
            db._client.table("organization_members")
            .select("id", count="exact")
            .eq("organization_id", org_id)
            .execute()
        )

        return {
            **org.data,
            "my_role": member.data["role"],
            "member_count": members.count or 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get org", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch organization")


# ── Members ──────────────────────────────────────────────────────

@router.get("/{org_id}/members")
async def list_members(org_id: str, user: dict = Depends(get_current_user)):
    """List all members of an organization."""
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        result = (
            db._client.table("organization_members")
            .select("id, user_id, role, joined_at, profiles(full_name, avatar_url, email:id)")
            .eq("organization_id", org_id)
            .order("joined_at")
            .execute()
        )
        return {"members": result.data or []}
    except Exception as e:
        logger.error("Failed to list members", error=str(e))
        return {"members": []}


@router.patch("/{org_id}/members/{member_user_id}/role")
async def update_member_role(
    org_id: str,
    member_user_id: str,
    body: RoleUpdateRequest,
    request: Request,
    user: dict = Depends(require_minimum_role("admin")),
):
    """Update a member's role (admin+ only)."""
    from app.models.database import get_db_service
    db = get_db_service()

    if body.role not in ROLE_HIERARCHY:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")

    # Can't assign a role higher than your own
    my_level = ROLE_HIERARCHY.get(user.get("role", "viewer"), 0)
    target_level = ROLE_HIERARCHY.get(body.role, 0)
    if target_level > my_level:
        raise HTTPException(status_code=403, detail="Cannot assign a role higher than your own")

    try:
        db._client.table("organization_members").update(
            {"role": body.role}
        ).eq("organization_id", org_id).eq("user_id", member_user_id).execute()

        await log_audit_event(
            user_id=user["id"],
            action="update_member_role",
            resource_type="organization_member",
            resource_id=member_user_id,
            org_id=org_id,
            details={"new_role": body.role},
            request=request,
        )

        return {"success": True, "user_id": member_user_id, "new_role": body.role}
    except Exception as e:
        logger.error("Failed to update role", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update member role")


@router.delete("/{org_id}/members/{member_user_id}")
async def remove_member(
    org_id: str,
    member_user_id: str,
    request: Request,
    user: dict = Depends(require_minimum_role("admin")),
):
    """Remove a member from the organization (admin+ only)."""
    from app.models.database import get_db_service
    db = get_db_service()

    if member_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot remove yourself. Transfer ownership first.")

    try:
        db._client.table("organization_members").delete().eq(
            "organization_id", org_id
        ).eq("user_id", member_user_id).execute()

        await log_audit_event(
            user_id=user["id"],
            action="remove_member",
            resource_type="organization_member",
            resource_id=member_user_id,
            org_id=org_id,
            request=request,
        )

        return {"success": True, "removed_user_id": member_user_id}
    except Exception as e:
        logger.error("Failed to remove member", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to remove member")


# ── Invitations ──────────────────────────────────────────────────

@router.post("/{org_id}/invitations")
async def create_invitation(
    org_id: str,
    body: InviteRequest,
    request: Request,
    user: dict = Depends(require_permission("invite_members")),
):
    """Send an invitation to join the organization."""
    from app.models.database import get_db_service
    db = get_db_service()

    if body.role not in ROLE_HIERARCHY:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")

    token = secrets.token_urlsafe(32)

    try:
        invitation = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "email": body.email,
            "role": body.role,
            "invited_by": user["id"],
            "token": token,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = db._client.table("invitations").insert(invitation).execute()

        # Send Email
        org = db._client.table("organizations").select("name").eq("id", org_id).single().execute()
        org_name = org.data["name"] if org.data else "Your Organization"
        
        from app.services.mailer import send_invite_email
        email_sent = send_invite_email(body.email, org_name, body.role, token)

        await log_audit_event(
            user_id=user["id"],
            action="create_invitation",
            resource_type="invitation",
            resource_id=invitation["id"],
            org_id=org_id,
            details={"email": body.email, "role": body.role, "email_sent": email_sent},
            request=request,
        )

        return {
            "invitation_id": invitation["id"],
            "email": body.email,
            "role": body.role,
            "token": token,
            "invite_url": f"/invite/{token}",
            "email_sent": email_sent,
        }
    except Exception as e:
        logger.error("Failed to create invitation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create invitation")


@router.post("/invitations/{token}/accept")
async def accept_invitation(token: str, user: dict = Depends(get_current_user)):
    """Accept an invitation using the token."""
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        inv = db._client.table("invitations").select("*").eq("token", token).eq("status", "pending").single().execute()
        if not inv.data:
            raise HTTPException(status_code=404, detail="Invitation not found or already used")

        # Add as member
        membership = {
            "id": str(uuid.uuid4()),
            "organization_id": inv.data["organization_id"],
            "user_id": user["id"],
            "role": inv.data["role"],
            "invited_by": inv.data["invited_by"],
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        db._client.table("organization_members").insert(membership).execute()

        # Update invitation status
        db._client.table("invitations").update(
            {"status": "accepted"}
        ).eq("id", inv.data["id"]).execute()

        # Set current org
        db._client.table("profiles").update(
            {"current_org_id": inv.data["organization_id"]}
        ).eq("id", user["id"]).execute()

        return {
            "success": True,
            "organization_id": inv.data["organization_id"],
            "role": inv.data["role"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to accept invitation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to accept invitation")


# ── Audit Log ────────────────────────────────────────────────────

@router.get("/{org_id}/audit")
async def get_audit_log(
    org_id: str,
    limit: int = 50,
    user: dict = Depends(require_permission("view_audit_log")),
):
    """Get the audit log for an organization (admin+ only)."""
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        result = (
            db._client.table("audit_log")
            .select("*")
            .eq("organization_id", org_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"audit_log": result.data or [], "total": len(result.data or [])}
    except Exception as e:
        logger.error("Failed to get audit log", error=str(e))
        return {"audit_log": [], "total": 0}
