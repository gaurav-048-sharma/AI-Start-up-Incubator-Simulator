"""
Organization & Team API Routes — multi-tenant workspace management.
Handles org CRUD, member management, invitations, and audit log.

Key security invariants:
  - Org creation requires 'enterprise' tier OR platform super_admin.
  - Org admin role is TENANT-scoped — it NEVER grants platform privileges.
  - All org-scoped operations validate X-Org-Id → membership before proceeding.
  - SSO configuration requires tenant admin within the specific org.
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
    require_platform_role,
    require_feature,
    require_mfa_stepup,
    log_audit_event,
    ROLE_HIERARCHY,
    ROLE_DESCRIPTIONS,
    TENANT_ROLE_HIERARCHY,
    require_org_context,
)

logger = structlog.get_logger()
router = APIRouter()


# ── Request/Response Models ──────────────────────────────────────

class OrganizationMemberResponse(BaseModel):
    id: str
    user_id: str
    role: str
    joined_at: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class OrganizationResponse(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")

class OrgCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    parent_id: Optional[str] = None

class OrgUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    logo_url: Optional[str] = None
    settings: Optional[dict] = None

class InviteRequest(BaseModel):
    email: str = Field(..., description="Email to invite")
    role: str = Field(default="team_member", description="Role to assign")

class RoleUpdateRequest(BaseModel):
    role: str = Field(..., description="New role to assign")

class SSOConfigUpdateRequest(BaseModel):
    sso_provider: Optional[str] = Field(None, description="SSO Provider (e.g. okta, azure_ad)")
    sso_entity_id: Optional[str] = Field(None, description="Identity Provider Entity ID")
    sso_acs_url: Optional[str] = Field(None, description="Assertion Consumer Service URL")
    sso_x509_cert: Optional[str] = Field(None, description="Public Certificate")
    sso_enforced: Optional[bool] = Field(None, description="Require SSO login")

# ── Roles Info ───────────────────────────────────────────────────

@router.get("/roles")
async def list_roles():
    """List all available tenant roles with descriptions and hierarchy levels."""
    return {
        "roles": [
            {
                "id": role,
                "label": role.replace("_", " ").title(),
                "level": level,
                "description": ROLE_DESCRIPTIONS.get(role, ""),
            }
            for role, level in sorted(TENANT_ROLE_HIERARCHY.items(), key=lambda x: x[1])
        ]
    }


# ── Organization CRUD ────────────────────────────────────────────

@router.post("")
async def create_org(
    body: OrgCreate,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Create a new organization.
    Restricted to enterprise-tier users or platform super_admins.
    The creator becomes the org admin (tenant-scoped, NOT platform admin).
    """
    from app.models.database import get_db_service
    db = get_db_service()

    # Gate: only enterprise users or platform super_admins can create orgs
    if user.get("platform_role") != "super_admin":
        user_tier = user.get("tier", "free")
        if user_tier not in ("enterprise",):
            raise HTTPException(
                status_code=403,
                detail="Organization creation requires an Enterprise subscription. "
                       "Upgrade at /dashboard/settings or submit an enterprise request.",
            )

    org_id = str(uuid.uuid4())
    try:
        org_data = {
            "id": org_id,
            "name": body.name,
            "slug": body.slug,
            "parent_id": body.parent_id, # Link to parent (e.g. ai.org)
            "owner_id": user["id"],
            "plan": "enterprise" if user.get("platform_role") == "super_admin" else user.get("tier", "free"),
            "subscription_status": "active" if user.get("platform_role") == "super_admin" else "pending_payment",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        result = db._client.table("organizations").insert(org_data).execute()

        # Add creator as org admin (TENANT role only)
        membership = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": user["id"],
            "role": "admin",
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        db._client.table("organization_members").insert(membership).execute()

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
    """List organizations the current user belongs to. Super admins see all."""
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        if user.get("platform_role") == "super_admin":
            # Super admins see every organization globally
            result = (
                db._client.table("organizations")
                .select("id, name, slug, logo_url, plan, owner_id, subscription_status, created_at")
                .execute()
            )
            return {
                "organizations": [
                    {
                        **org,
                        "my_role": "super_admin",
                        "is_owner": org.get("owner_id") == user["id"],
                    }
                    for org in (result.data or [])
                ]
            }

        # Regular users only see orgs they are members of
        result = (
            db._client.table("organization_members")
            .select("organization_id, role, organizations(id, name, slug, logo_url, plan, owner_id, subscription_status, created_at)")
            .eq("user_id", user["id"])
            .execute()
        )
        return {
            "organizations": [
                {
                    "id": m["organizations"]["id"],
                    "name": m["organizations"]["name"],
                    "slug": m["organizations"]["slug"],
                    "logo_url": m["organizations"].get("logo_url"),
                    "plan": m["organizations"]["plan"],
                    "subscription_status": m["organizations"].get("subscription_status", "active"),
                    "my_role": m["role"],
                    "is_owner": m["organizations"].get("owner_id") == user["id"],
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
    """Get organization details (must be a member or platform super_admin)."""
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        org = db._client.table("organizations").select("*").eq("id", org_id).single().execute()
        if not org.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Check membership (super_admins bypass)
        my_role = None
        if user.get("platform_role") == "super_admin":
            my_role = "super_admin"
        else:
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
            my_role = member.data["role"]

        # Get member count
        members = (
            db._client.table("organization_members")
            .select("id", count="exact")
            .eq("organization_id", org_id)
            .execute()
        )

        return {
            **org.data,
            "my_role": my_role,
            "member_count": members.count or 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get org", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch organization")


@router.get("/{org_id}/members")
async def list_org_members(
    org_id: str,
    user: dict = Depends(get_current_user),
):
    """
    List members of an organization. 
    Platform super_admins can see all rosters. 
    Regular users must be a member of the specific organization.
    """
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        # 1. Super Admin Oversight
        is_super_admin = user.get("platform_role") == "super_admin"
        
        # 2. Membership Check (if not super admin)
        if not is_super_admin:
            member = (
                db._client.table("organization_members")
                .select("id")
                .eq("organization_id", org_id)
                .eq("user_id", user["id"])
                .single()
                .execute()
            )
            if not member.data:
                raise HTTPException(status_code=403, detail="Access denied: You are not a member of this department.")

        result = (
            db._client.table("organization_members")
            .select("id, user_id, role, joined_at, profiles!organization_members_user_id_fkey(full_name, avatar_url)")
            .eq("organization_id", org_id)
            .execute()
        )
        
        members = []
        for m in (result.data or []):
            profile = m.get("profiles!organization_members_user_id_fkey") or {}
            members.append({
                "id": m["id"],
                "user_id": m["user_id"],
                "role": m["role"],
                "joined_at": m["joined_at"],
                "full_name": profile.get("full_name"),
                "avatar_url": profile.get("avatar_url"),
            })
        return {"members": members}
    except Exception as e:
        logger.error("Failed to list org_members", error=str(e), org_id=org_id)
        raise HTTPException(status_code=500, detail="Failed to fetch members")


@router.patch("/{org_id}/sso")
async def update_org_sso(
    org_id: str,
    body: SSOConfigUpdateRequest,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_minimum_role("admin")),
):
    """Update SSO Configuration for an organization (org admin+ only)."""
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        data_to_update = {k: v for k, v in body.model_dump().items() if v is not None}
        if not data_to_update:
            raise HTTPException(status_code=400, detail="No SSO fields provided to update")

        db._client.table("organizations").update(data_to_update).eq("id", org_id).execute()

        await log_audit_event(
            user_id=user["id"],
            action="update_sso_config",
            resource_type="organization",
            resource_id=org_id,
            org_id=org_id,
            details={"updated_fields": list(data_to_update.keys())},
            request=request,
        )

        return {"success": True, "message": "SSO configuration updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update org SSO", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update SSO configuration")

# ── Members ──────────────────────────────────────────────────────

@router.get("/{org_id}/members")
async def list_members(org_id: str, user: dict = Depends(get_current_user)):
    """List all members of an organization."""
    from app.models.database import get_db_service
    db = get_db_service()

    # Verify membership or platform role
    if user.get("platform_role") != "super_admin":
        member_check = (
            db._client.table("organization_members")
            .select("id")
            .eq("organization_id", org_id)
            .eq("user_id", user["id"])
            .execute()
        )
        if not (member_check.data):
            raise HTTPException(status_code=403, detail="You are not a member of this organization")

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
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_minimum_role("admin")),
):
    """Update a member's tenant role (org admin+ only)."""
    from app.models.database import get_db_service
    db = get_db_service()

    # Validate the role is a valid TENANT role (not a platform role)
    if body.role not in TENANT_ROLE_HIERARCHY:
        raise HTTPException(status_code=400, detail=f"Invalid tenant role: {body.role}")

    # Can't assign a role higher than your own (within tenant scope)
    my_level = TENANT_ROLE_HIERARCHY.get(user.get("org_role", "viewer"), 0)
    target_level = TENANT_ROLE_HIERARCHY.get(body.role, 0)
    if target_level > my_level and user.get("platform_role") != "super_admin":
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
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_minimum_role("admin")),
):
    """Remove a member from the organization (org admin+ only)."""
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
    user: dict = Depends(require_mfa_stepup()),
    _perm: dict = Depends(require_permission("invite_members")),
):
    """Send an invitation to join the organization."""
    from app.models.database import get_db_service
    db = get_db_service()

    if body.role not in TENANT_ROLE_HIERARCHY:
        raise HTTPException(status_code=400, detail=f"Invalid tenant role: {body.role}")

    # Check seat limits
    try:
        org = db._client.table("organizations").select("max_members").eq("id", org_id).single().execute()
        if org.data:
            current_members = (
                db._client.table("organization_members")
                .select("id", count="exact")
                .eq("organization_id", org_id)
                .execute()
            )
            if current_members.count and org.data.get("max_members"):
                if current_members.count >= org.data["max_members"]:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Organization has reached its seat limit ({org.data['max_members']}). "
                               "Upgrade your plan to add more members.",
                    )
    except HTTPException:
        raise
    except Exception:
        pass  # Non-blocking check

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
        db._client.table("invitations").insert(invitation).execute()

        # Send Email
        org_result = db._client.table("organizations").select("name").eq("id", org_id).single().execute()
        org_name = org_result.data["name"] if org_result.data else "Your Organization"

        email_sent = False
        try:
            from app.services.mailer import send_invite_email
            email_sent = send_invite_email(body.email, org_name, body.role, token)
        except Exception:
            pass

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
    except HTTPException:
        raise
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
    """Get the audit log for an organization (org admin+ only)."""
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
