"""
Reports API Routes — Report retrieval and download.
"""

import structlog
from fastapi import APIRouter, HTTPException
from app.models.database import get_db_service
from app.models.schemas import ReportResponse

logger = structlog.get_logger()
router = APIRouter()


@router.get("/ideas/{idea_id}", response_model=list[ReportResponse])
async def get_idea_reports(idea_id: str):
    """Get all reports for an idea."""
    db = get_db_service()
    reports = await db.get_idea_reports(idea_id)
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Get a specific report by ID."""
    db = get_db_service()
    report = await db.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
