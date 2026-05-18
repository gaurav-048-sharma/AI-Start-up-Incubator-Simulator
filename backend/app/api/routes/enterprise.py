import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import uuid
import secrets

from app.models.database import get_db_service
from app.middleware.security import require_minimum_role
from app.services.mailer import send_invite_email

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

@router.get("/requests")
def list_enterprise_requests(user: dict = Depends(require_minimum_role("super_admin"))):
    """List all enterprise requests for super admins."""
    db = get_db_service()
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    try:
        result = db._client.table("enterprise_requests").select("*").order("created_at", desc=True).execute()
        return {"requests": result.data or []}
    except Exception as e:
        logger.error("Failed to list enterprise requests", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list requests")


@router.post("/request")
def submit_enterprise_request(request: EnterpriseRequest):
    """Submit a request for enterprise access."""
    db = get_db_service()
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    try:
        result = db._client.table("enterprise_requests").insert(request.model_dump()).execute()
        return {"status": "success", "message": "Enterprise request received.", "id": result.data[0]["id"]}
    except Exception as e:
        logger.error("Failed to submit enterprise request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to submit request")

@router.post("/approve/{request_id}")
def approve_enterprise_request(request_id: str, user: dict = Depends(require_minimum_role("super_admin"))):
    """Approve an enterprise request, provision an organization, and email the invite."""
    db = get_db_service()
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")

    req = db._client.table("enterprise_requests").select("*").eq("id", request_id).execute()
    if not req.data:
        raise HTTPException(status_code=404, detail="Enterprise request not found")
        
    req_data = req.data[0]
    if req_data["status"] == "approved":
        raise HTTPException(status_code=400, detail="This request has already been approved")

    try:
        # 1. Create the enterprise organization
        slug = req_data["company_name"].lower().replace(" ", "-") + "-" + str(uuid.uuid4())[:6]
        org_res = db._client.table("organizations").insert({
            "name": req_data["company_name"],
            "slug": slug,
            "plan": "enterprise",
            "max_members": req_data["required_seats"] or 50,
            "max_ideas": 100
        }).execute()
        org_id = org_res.data[0]["id"]

        # 2. Create the invitation for the contact person to join as incubator_manager
        token = secrets.token_urlsafe(32)
        db._client.table("invitations").insert({
            "organization_id": org_id,
            "email": req_data["contact_email"],
            "role": "incubator_manager",
            "invited_by": user["id"],
            "token": token
        }).execute()

        # 3. Update the request status
        db._client.table("enterprise_requests").update({"status": "approved"}).eq("id", request_id).execute()

        # 4. Dispatch the SMTP email
        send_invite_email(req_data["contact_email"], req_data["company_name"], "incubator_manager", token)

        return {
            "status": "success", 
            "message": "Enterprise provisioned and invitation sent.",
            "organization_id": org_id
        }
    except Exception as e:
        logger.error("Failed to provision enterprise", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to provision enterprise")

@router.get("/organizations")
def list_all_organizations(user: dict = Depends(require_minimum_role("super_admin"))):
    """List all organizations globally for super admins."""
    db = get_db_service()
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    try:
        # Try to select with status first
        result = db._client.table("organizations").select("id, name, slug, plan, max_members, status, created_at").order("created_at", desc=True).execute()
        return {"organizations": result.data or []}
    except Exception as e:
        if "Could not find the 'status' column" in str(e) or "column" in str(e).lower():
            # Fallback for when the migration hasn't been applied yet
            result = db._client.table("organizations").select("id, name, slug, plan, max_members, created_at").order("created_at", desc=True).execute()
            orgs = result.data or []
            for org in orgs:
                org["status"] = "active" # Default fallback
            return {"organizations": orgs}
        logger.error("Failed to list all organizations", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list organizations")

@router.delete("/organizations/{org_id}")
def delete_organization(org_id: str, user: dict = Depends(require_minimum_role("super_admin"))):
    """Delete an organization globally."""
    db = get_db_service()
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    try:
        # Clear foreign keys that lack ON DELETE CASCADE
        db._client.table("profiles").update({"current_org_id": None}).eq("current_org_id", org_id).execute()
        db._client.table("ideas").update({"organization_id": None}).eq("organization_id", org_id).execute()
        
        # Now delete the organization
        db._client.table("organizations").delete().eq("id", org_id).execute()
        return {"status": "success", "message": "Organization deleted"}
    except Exception as e:
        logger.error("Failed to delete organization", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete organization")

class OrgStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|suspended)$")

@router.patch("/organizations/{org_id}/status")
def update_organization_status(org_id: str, payload: OrgStatusUpdate, user: dict = Depends(require_minimum_role("super_admin"))):
    """Suspend or reactivate an organization globally."""
    db = get_db_service()
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    try:
        db._client.table("organizations").update({"status": payload.status}).eq("id", org_id).execute()
        return {"status": "success", "message": f"Organization {payload.status}"}
    except Exception as e:
        if "Could not find the 'status' column" in str(e) or "column" in str(e).lower():
            raise HTTPException(status_code=501, detail="Organization suspension is not available yet. Please run migration 004_org_suspension.sql.")
        logger.error("Failed to update organization status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update organization status")

