"""
Enterprise API Routes — Platform-level administration.
All endpoints require platform_role: super_admin.
These are NEVER accessible to tenant-scoped org admins.
"""

import structlog
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional
# uuid imported locally where needed (e.g. in billing webhook handler)

from app.models.database import get_db_service
from app.middleware.security import (
    require_platform_role,
    require_mfa_stepup,
    log_audit_event,
)

logger = structlog.get_logger()
router = APIRouter()


class EnterpriseRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    contact_name: str = Field(..., min_length=2, max_length=150)
    contact_email: str = Field(..., pattern=r"^\S+@\S+\.\S+$")
    team_size: Optional[str] = None
    industry: Optional[str] = None
    use_case: Optional[str] = None
    required_seats: Optional[int] = Field(None, ge=1)
    compliance_requirements: Optional[str] = None
    white_label_needs: bool = False
    billing_preferences: Optional[str] = None
    notes: Optional[str] = None


# ── Enterprise Access Requests ───────────────────────────────────

@router.get("/requests")
async def list_enterprise_requests(
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_platform_role("super_admin")),
):
    """List all enterprise requests. Platform super_admin only."""
    db = get_db_service()
    try:
        result = (
            db._client.table("enterprise_requests")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return {"requests": result.data or []}
    except Exception as e:
        logger.error("Failed to list enterprise requests", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list requests")


@router.post("/request")
async def submit_enterprise_request(body: EnterpriseRequest):
    """Submit a request for enterprise access. Public endpoint."""
    db = get_db_service()
    try:
        result = db._client.table("enterprise_requests").insert(body.model_dump()).execute()
        return {
            "status": "success",
            "message": "Enterprise request received. Our team will review and reach out.",
            "id": result.data[0]["id"],
        }
    except Exception as e:
        logger.error("Failed to submit enterprise request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to submit request")


@router.post("/approve/{request_id}")
async def approve_enterprise_request(
    request_id: str,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_platform_role("super_admin")),
):
    """
    Approve an enterprise request.
    Transitions to pending_payment — does NOT provision immediately.
    In production, this generates a Stripe Checkout link and emails it.
    """
    db = get_db_service()

    req = db._client.table("enterprise_requests").select("*").eq("id", request_id).execute()
    if not req.data:
        raise HTTPException(status_code=404, detail="Enterprise request not found")

    req_data = req.data[0]
    if req_data["status"] in ("approved", "pending_payment"):
        raise HTTPException(status_code=400, detail="This request has already been processed")

    try:
        from app.config import get_settings
        settings = get_settings()

        # Generate checkout link (Stripe in production, mock otherwise)
        checkout_url = f"{settings.frontend_url}/enterprise/checkout?req={request_id}"

        if settings.stripe_secret_key:
            try:
                import stripe
                stripe.api_key = settings.stripe_secret_key
                session = stripe.checkout.Session.create(
                    mode="subscription",
                    line_items=[{"price": settings.stripe_price_enterprise, "quantity": 1}],
                    success_url=f"{settings.frontend_url}/enterprise/welcome?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=f"{settings.frontend_url}/enterprise?canceled=true",
                    customer_email=req_data["contact_email"],
                    metadata={
                        "enterprise_request_id": request_id,
                        "company_name": req_data["company_name"],
                    },
                )
                checkout_url = session.url
            except Exception as stripe_err:
                logger.warning("Stripe checkout creation failed, using mock", error=str(stripe_err))

        # Transition to pending_payment
        db._client.table("enterprise_requests").update({
            "status": "pending_payment",
        }).eq("id", request_id).execute()

        # Send email with checkout link
        try:
            from app.services.mailer import send_invite_email
            send_invite_email(
                req_data["contact_email"],
                req_data["company_name"],
                "enterprise_admin",
                checkout_url,
            )
        except Exception:
            logger.warning("Email dispatch failed for enterprise approval")

        await log_audit_event(
            user_id=user["id"],
            action="approve_enterprise_request",
            resource_type="enterprise_request",
            resource_id=request_id,
            details={"company": req_data["company_name"], "status": "pending_payment"},
            request=request,
        )

        return {
            "status": "success",
            "message": "Enterprise request approved. Payment link dispatched.",
            "checkout_url": checkout_url,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to approve enterprise request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to approve enterprise request")


@router.post("/provision/{request_id}")
async def provision_enterprise_request(
    request_id: str,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_platform_role("super_admin")),
):
    """
    Provision an enterprise org immediately from a paid enterprise_request.
    Super admin only. This calls a server-side RPC that validates approval and creates the org.
    """
    from app.models.database import get_supabase_client
    admin_client = get_supabase_client(admin=True)
    try:
        # Call RPC - must use admin client since execute privileges are revoked from PUBLIC
        res = admin_client.rpc("create_organization_from_request", {"req_id": request_id, "approver_id": user["id"]}).execute()
        # Supabase returns result in res.data for RPC calls
        new_org_id = None
        if hasattr(res, 'data') and res.data:
            # Could be a list or scalar
            if isinstance(res.data, list):
                new_org_id = res.data[0]
            else:
                new_org_id = res.data

        await log_audit_event(
            user_id=user["id"],
            action="provision_enterprise_request",
            resource_type="enterprise_request",
            resource_id=request_id,
            details={"new_org_id": new_org_id},
            request=request,
        )
        return {"status": "success", "org_id": new_org_id}
    except Exception as e:
        logger.error("Failed to provision enterprise org", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to provision enterprise org")


@router.post("/reject/{request_id}")
async def reject_enterprise_request(
    request_id: str,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_platform_role("super_admin")),
):
    """Reject an enterprise request."""
    db = get_db_service()
    try:
        db._client.table("enterprise_requests").update({
            "status": "rejected",
        }).eq("id", request_id).execute()

        await log_audit_event(
            user_id=user["id"],
            action="reject_enterprise_request",
            resource_type="enterprise_request",
            resource_id=request_id,
            request=request,
        )

        return {"status": "success", "message": "Enterprise request rejected."}
    except Exception as e:
        logger.error("Failed to reject enterprise request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to reject request")


# ── Global Organization Management (Platform Admin) ──────────────

@router.get("/organizations")
async def list_all_organizations(
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_platform_role("support")),
):
    """List all organizations globally. Platform support+ role required."""
    db = get_db_service()
    try:
        result = (
            db._client.table("organizations")
            .select("id, name, slug, plan, max_members, status, subscription_status, created_at")
            .order("created_at", desc=True)
            .execute()
        )
        return {"organizations": result.data or []}
    except Exception as e:
        # Fallback for missing columns
        try:
            result = (
                db._client.table("organizations")
                .select("id, name, slug, plan, max_members, created_at")
                .order("created_at", desc=True)
                .execute()
            )
            orgs = result.data or []
            for org in orgs:
                org.setdefault("status", "active")
                org.setdefault("subscription_status", "active")
            return {"organizations": orgs}
        except Exception:
            pass
        logger.error("Failed to list all organizations", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list organizations")


@router.delete("/organizations/{org_id}")
async def delete_organization(
    org_id: str,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_platform_role("super_admin")),
):
    """Delete an organization globally. Super admin only."""
    db = get_db_service()
    try:
        # Cascade cleanup: remove members, invitations, and orphaned data
        db._client.table("organization_members").delete().eq("organization_id", org_id).execute()
        db._client.table("invitations").delete().eq("organization_id", org_id).execute()
        db._client.table("ideas").update({"organization_id": None}).eq("organization_id", org_id).execute()
        db._client.table("organizations").delete().eq("id", org_id).execute()

        await log_audit_event(
            user_id=user["id"],
            action="delete_organization",
            resource_type="organization",
            resource_id=org_id,
            request=request,
        )

        return {"status": "success", "message": "Organization deleted"}
    except Exception as e:
        logger.error("Failed to delete organization", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete organization")


class OrgStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|suspended)$")


@router.patch("/organizations/{org_id}/status")
async def update_organization_status(
    org_id: str,
    payload: OrgStatusUpdate,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_platform_role("super_admin")),
):
    """Suspend or reactivate an organization. Super admin only."""
    db = get_db_service()
    try:
        db._client.table("organizations").update({"status": payload.status}).eq("id", org_id).execute()

        await log_audit_event(
            user_id=user["id"],
            action="update_org_status",
            resource_type="organization",
            resource_id=org_id,
            details={"new_status": payload.status},
            request=request,
        )

        return {"status": "success", "message": f"Organization {payload.status}"}
    except Exception as e:
        if "column" in str(e).lower():
            raise HTTPException(
                status_code=501,
                detail="Organization suspension not available. Run migration 007.",
            )
        logger.error("Failed to update organization status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update organization status")


# ── Platform User Management ─────────────────────────────────────

@router.get("/users")
async def list_platform_users(
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_platform_role("support")),
    limit: int = 100,
):
    """List all platform users. Support+ role required."""
    db = get_db_service()
    try:
        result = (
            db._client.table("profiles")
            .select("id, full_name, role, platform_role, tier, credits, created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"users": result.data or []}
    except Exception as e:
        logger.error("Failed to list users", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list users")


class PlatformRoleUpdate(BaseModel):
    platform_role: str = Field(..., pattern="^(user|support|billing_admin|super_admin)$")


@router.patch("/users/{user_id}/platform-role")
async def update_user_platform_role(
    user_id: str,
    payload: PlatformRoleUpdate,
    request: Request,
    user: dict = Depends(require_mfa_stepup()),
    _role: dict = Depends(require_platform_role("super_admin")),
):
    """Update a user's platform role. Super admin only."""
    db = get_db_service()

    # Prevent self-demotion
    if user_id == user["id"] and payload.platform_role != "super_admin":
        raise HTTPException(status_code=400, detail="Cannot demote yourself")

    try:
        db._client.table("profiles").update({
            "platform_role": payload.platform_role,
        }).eq("id", user_id).execute()

        # Invalidate the cache to apply new role immediately
        from app.middleware.security import invalidate_profile_cache
        invalidate_profile_cache(user_id)

        await log_audit_event(
            user_id=user["id"],
            action="update_platform_role",
            resource_type="user",
            resource_id=user_id,
            details={"new_platform_role": payload.platform_role},
            request=request,
        )

        return {"status": "success", "user_id": user_id, "platform_role": payload.platform_role}
    except Exception as e:
        logger.error("Failed to update platform role", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update platform role")
