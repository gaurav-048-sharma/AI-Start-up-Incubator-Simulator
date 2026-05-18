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
