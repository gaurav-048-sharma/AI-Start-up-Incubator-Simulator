"""
Reports API Routes — Report retrieval and download.
All endpoints require authentication with strict organization context.
"""

import structlog
from fastapi import APIRouter, HTTPException, Depends
from app.models.database import get_db_service
from app.models.schemas import ReportResponse
from app.middleware.security import (
    get_current_user, 
    require_org_context,
    require_permission,
    require_mfa_stepup,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/ideas/{idea_id}", response_model=list[ReportResponse])
async def get_idea_reports(
    idea_id: str, 
    user: dict = Depends(get_current_user),
    _org: dict = Depends(require_org_context()),
):
    """
    Get all reports for an idea.
    Verified against active organization context.
    """
    db = get_db_service()
    
    # 1. Fetch current idea state to verify organization
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    # 2. Scope verification
    if user.get("platform_role") != "super_admin":
        if idea.get("organization_id") != user.get("org_id"):
             raise HTTPException(status_code=403, detail="Access denied: idea belongs to a different organization")

    reports = await db.get_idea_reports(idea_id)
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str, 
    user: dict = Depends(get_current_user),
    _org: dict = Depends(require_org_context()),
):
    """
    Get a specific report by ID.
    Verified against active organization context.
    """
    db = get_db_service()
    report = await db.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Scope verification
    if user.get("platform_role") != "super_admin":
        if report.get("organization_id") != user.get("org_id"):
             raise HTTPException(status_code=403, detail="Access denied")

    return report
