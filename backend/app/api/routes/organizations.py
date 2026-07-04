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

import app.models.database as database
from app.models.database import get_db_service

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
    ASSIGNABLE_TENANT_ROLES,
    ORG_OWNER_ROLE,
    WORKSPACE_OWNER_ROLE,
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
    role: str = Field(default="member", description="Role to assign")
    department_id: Optional[str] = Field(default=None, description="Department to assign")

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
    # Use TENANT_ROLE_HIERARCHY explicitly to ensure platform roles remain private.
    return {
        "roles": [
            {
                "id": role,
                "label": role.replace("_", " ").title(),
                "level": level,
                "description": ROLE_DESCRIPTIONS.get(role, ""),
                "assignable": role in ASSIGNABLE_TENANT_ROLES,
            }
            for role, level in sorted(TENANT_ROLE_HIERARCHY.items(), key=lambda x: x[1])
            if role != ORG_OWNER_ROLE
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
    db = get_db_service()

    # Gate: platform super_admins bypass. For root org creation (no parent_id),
    # the user must be on an Enterprise tier. For child org creation (parent_id
    # provided), allow tenant admins/owners of the parent org to create the child.
    if user.get("platform_role") == "super_admin":
        pass
    else:
        if body.parent_id:
            # Verify the user is an admin/incubator_manager or owner of the parent org
            try:
                member = (
                    db._client.table("organization_members")
                    .select("role")
                    .eq("organization_id", body.parent_id)
                    .eq("user_id", user["id"])
                    .single()
                    .execute()
                )
                owner_check = (
                    db._client.table("organizations")
                    .select("owner_id")
                    .eq("id", body.parent_id)
                    .single()
                    .execute()
                )

                is_owner = False
                member_role = None
                if owner_check.data and owner_check.data.get("owner_id") == user["id"]:
                    is_owner = True
                    member_role = WORKSPACE_OWNER_ROLE
                elif member.data:
                    member_role = member.data.get("role")

                if not (is_owner or (member_role in ("org_admin", "org_owner"))):
                    raise HTTPException(
                        status_code=403,
                        detail="Only organization admins or owners may create sub-organizations.",
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning("Parent org verification failed", error=str(e), parent_id=body.parent_id)
                raise HTTPException(status_code=403, detail="Unable to verify parent organization permissions")
        else:
            # Root org creation: ONLY platform super_admins can create root organizations directly.
            # Enterprise tier users must go through the Request -> Approval -> Payment flow
            # which triggers the secure provisioning RPC or background task.
            raise HTTPException(
                status_code=403,
                detail="Direct root organization creation is restricted to platform administrators. "
                       "Please submit an enterprise request at /enterprise to begin onboarding.",
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

        # Add creator as org admin (TENANT role only) — must use admin client due to RLS
        admin_client = database.get_supabase_client(admin=True)
        membership = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": user["id"],
            "role": "org_admin",
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        admin_client.table("organization_members").insert(membership).execute()

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
    db = get_db_service()

    try:
        if user.get("platform_role") == "super_admin":
            # Super admins see every organization globally
            result = (
                db._client.table("organizations")
                .select("id, name, slug, logo_url, plan, owner_id, subscription_status, created_at")
                .execute()
            )
            orgs = result.data or []
            # Fetch member counts for each org for super_admin insight
            enriched = []
            for org in orgs:
                try:
                    members = (
                        db._client.table("organization_members")
                        .select("id", count="exact")
                        .eq("organization_id", org.get("id"))
                        .execute()
                    )
                    member_count = members.count or 0
                except Exception:
                    member_count = 0

                enriched.append({
                    **org,
                    "my_role": "super_admin",
                    "is_owner": org.get("owner_id") == user["id"],
                    "member_count": member_count,
                })

            return {"organizations": enriched}

        # Regular users only see orgs they are members of
        result = (
            db._client.table("organization_members")
            .select("organization_id, role, organizations(id, name, slug, logo_url, plan, owner_id, subscription_status, created_at)")
            .eq("user_id", user["id"])
            .execute()
        )
        organizations = []
        for m in (result.data or []):
            if not m.get("organizations"):
                continue
            org = m["organizations"]
            is_owner = org.get("owner_id") == user["id"]
            organizations.append({
                "id": org["id"],
                "name": org["name"],
                "slug": org["slug"],
                "logo_url": org.get("logo_url"),
                "plan": org["plan"],
                "subscription_status": org.get("subscription_status", "active"),
                "my_role": ORG_OWNER_ROLE if is_owner else m["role"],
                "is_owner": is_owner,
            })

        return {"organizations": organizations}
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
            is_owner = False
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
            is_owner = org.data.get("owner_id") == user["id"]
            my_role = ORG_OWNER_ROLE if is_owner else member.data["role"]

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
            "is_owner": is_owner,
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
    _role: dict = Depends(require_minimum_role("org_admin")),
):
    """Update SSO Configuration for an organization (org admin+ only)."""
    # IDOR Protection: ensure user is a member of the org they are updating
    if user.get("platform_role") != "super_admin":
        if user.get("org_id") != org_id:
            raise HTTPException(status_code=403, detail="Access denied: organization scope mismatch.")
    
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




@router.patch("/{org_id}/members/{member_user_id}/role")
async def update_member_role(
    org_id: str,
    member_user_id: str,
    body: RoleUpdateRequest,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_minimum_role("org_admin")),
):
    """Update a member's tenant role (org admin+ only)."""
    # IDOR Protection
    if user.get("platform_role") != "super_admin":
        if user.get("org_id") != org_id:
            raise HTTPException(status_code=403, detail="Access denied: organization scope mismatch.")
    from app.models.database import get_db_service
    db = get_db_service()

    # Validate the role is a valid TENANT role (not a platform role)
    if body.role not in ASSIGNABLE_TENANT_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid tenant role: {body.role}")

    # Can't assign a role higher than your own (within tenant scope)
    my_level = TENANT_ROLE_HIERARCHY.get(user.get("org_role", "viewer"), 0)
    target_level = TENANT_ROLE_HIERARCHY.get(body.role, 0)
    if target_level > my_level and user.get("platform_role") != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot assign a role higher than your own")

    try:
        admin_client = database.get_supabase_client(admin=True)
        admin_client.table("organization_members").update(
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
    _role: dict = Depends(require_minimum_role("org_admin")),
):
    """Remove a member from the organization (org admin+ only)."""
    # IDOR Protection
    if user.get("platform_role") != "super_admin":
        if user.get("org_id") != org_id:
            raise HTTPException(status_code=403, detail="Access denied: organization scope mismatch.")
    db = get_db_service()

    if member_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot remove yourself. Transfer ownership first.")

    try:
        admin_client = database.get_supabase_client(admin=True)
        admin_client.table("organization_members").delete().eq(
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
    # IDOR Protection
    if user.get("platform_role") != "super_admin":
        if user.get("org_id") != org_id:
            raise HTTPException(status_code=403, detail="Access denied: organization scope mismatch.")
    db = get_db_service()

    if body.role not in ASSIGNABLE_TENANT_ROLES:
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

        # Use admin client to bypass RLS for membership creation
        admin_client = database.get_supabase_client(admin=True)
        admin_client.table("organization_members").insert(membership).execute()

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


# ── Departments ──────────────────────────────────────────────────

class DeptCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")


@router.post("/{org_id}/departments")
async def create_department(
    org_id: str,
    body: DeptCreate,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_minimum_role("org_admin")),
):
    """Create a department within an organization (org admin+ only)."""
    if user.get("platform_role") != "super_admin":
        if user.get("org_id") != org_id:
            raise HTTPException(status_code=403, detail="Access denied: organization scope mismatch.")
    db = get_db_service()

    dept_id = str(uuid.uuid4())
    try:
        dept_data = {
            "id": dept_id,
            "name": body.name,
            "slug": body.slug,
            "parent_id": org_id,
            "is_department": True,
            "plan": "enterprise",
            "subscription_status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        result = db._client.table("organizations").insert(dept_data).execute()

        await log_audit_event(
            user_id=user["id"],
            action="create_department",
            resource_type="department",
            resource_id=dept_id,
            org_id=org_id,
            details={"name": body.name, "slug": body.slug},
            request=request,
        )

        return result.data[0] if result.data else dept_data
    except Exception as e:
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Department slug '{body.slug}' already exists")
        logger.error("Failed to create department", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create department")


@router.get("/{org_id}/departments")
async def list_departments(
    org_id: str,
    user: dict = Depends(get_current_user),
    _org: dict = Depends(require_org_context()),
):
    """List departments within an organization."""
    if user.get("platform_role") != "super_admin":
        if user.get("org_id") != org_id:
            raise HTTPException(status_code=403, detail="Access denied: organization scope mismatch.")
    db = get_db_service()

    try:
        result = (
            db._client.table("organizations")
            .select("id, name, slug, created_at")
            .eq("parent_id", org_id)
            .eq("is_department", True)
            .execute()
        )
        return {"departments": result.data or []}
    except Exception as e:
        logger.error("Failed to list departments", error=str(e))
        return {"departments": []}


@router.delete("/{org_id}/departments/{dept_id}")
async def delete_department(
    org_id: str,
    dept_id: str,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_minimum_role("org_admin")),
):
    """Delete a department (org admin+ only). Members are reassigned to the parent org."""
    if user.get("platform_role") != "super_admin":
        if user.get("org_id") != org_id:
            raise HTTPException(status_code=403, detail="Access denied: organization scope mismatch.")
    db = get_db_service()

    try:
        # Verify the department belongs to this org
        dept = db._client.table("organizations").select("parent_id, is_department").eq("id", dept_id).single().execute()
        if not dept.data or not dept.data.get("is_department") or dept.data.get("parent_id") != org_id:
            raise HTTPException(status_code=404, detail="Department not found in this organization")

        # Clear department_id from members (reassign to parent org)
        admin_client = database.get_supabase_client(admin=True)
        admin_client.table("organization_members").update(
            {"department_id": None}
        ).eq("department_id", dept_id).execute()

        # Clear department_id from ideas
        admin_client.table("ideas").update(
            {"department_id": None}
        ).eq("department_id", dept_id).execute()

        # Delete the department
        db._client.table("organizations").delete().eq("id", dept_id).execute()

        await log_audit_event(
            user_id=user["id"],
            action="delete_department",
            resource_type="department",
            resource_id=dept_id,
            org_id=org_id,
            request=request,
        )

        return {"success": True, "deleted_department_id": dept_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete department", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete department")


# ── Audit Log ────────────────────────────────────────────────────

@router.get("/{org_id}/audit")
async def get_audit_log(
    org_id: str,
    limit: int = 50,
    user: dict = Depends(require_permission("view_audit_log")),
):
    """Get the audit log for an organization (org admin+ only)."""
    # IDOR Protection
    if user.get("platform_role") != "super_admin":
        if user.get("org_id") != org_id:
            raise HTTPException(status_code=403, detail="Access denied: organization scope mismatch.")
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
