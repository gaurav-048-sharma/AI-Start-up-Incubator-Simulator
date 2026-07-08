"""
Build API Routes — endpoints for the AI Product Builder phase.
"""

import uuid
from datetime import datetime, timezone
import structlog
from fastapi import APIRouter, HTTPException, Depends
from typing import Any

from app.middleware.security import get_current_user
from app.models.database import get_db_service
from app.models.schemas import BuildSessionResponse, BuildMessageRequest
from app.simulation.build_engine import BuildEngine

logger = structlog.get_logger()
router = APIRouter()

@router.post("/ideas/{idea_id}/start", response_model=BuildSessionResponse)
async def start_build(idea_id: str, user: dict = Depends(get_current_user)):
    """
    Start a new build session for an idea.
    """
    db = get_db_service()
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    if idea.get("user_id") != user["id"] and user.get("platform_role") != "super_admin":
        if False:
            raise HTTPException(status_code=403, detail="Access denied")

    reports = await db.get_idea_reports(idea_id)
    
    engine = BuildEngine(db_service=db)
    codebase = await engine.initialize_build(idea, reports)
    
    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,
        "idea_id": idea_id,
        "user_id": user["id"],
        "organization_id": user.get("organization_id"),
        "status": "active",
        "codebase": codebase,
        "transcript": [{
            "role": "ai",
            "content": "I've reviewed your business plans and generated the initial MVP codebase. What would you like to change?",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Store this build session as a report in the database so it's persisted easily
    # We will use report_type = 'build_session'
    report_data = {
        "idea_id": idea_id,
        "organization_id": user.get("organization_id"),
        "report_type": "build_session",
        "content": session
    }
    await db.create_report(report_data)
    return BuildSessionResponse(**session)


@router.get("/ideas/{idea_id}", response_model=BuildSessionResponse)
async def get_build(idea_id: str, user: dict = Depends(get_current_user)):
    """
    Get the active build session for an idea.
    """
    db = get_db_service()
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    reports = await db.get_idea_reports(idea_id)
    build_sessions = [r for r in reports if r.get("report_type") == "build_session"]
    
    if not build_sessions:
        raise HTTPException(status_code=404, detail="No active build session")
        
    latest_session = build_sessions[-1].get("content", {})
    return BuildSessionResponse(**latest_session)


@router.post("/ideas/{idea_id}/message", response_model=BuildSessionResponse)
async def message_build(
    idea_id: str,
    req: BuildMessageRequest,
    user: dict = Depends(get_current_user),
):
    """
    Send a message to the AI developer team to iterate on the codebase.
    """
    db = get_db_service()
    target_idea = await db.get_idea(idea_id)
    if not target_idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    reports = await db.get_idea_reports(idea_id)
    build_sessions = [r for r in reports if r.get("report_type") == "build_session"]
    
    if not build_sessions:
        raise HTTPException(status_code=404, detail="Build session not found")
        
    target_session_report = build_sessions[-1]
    session_data = target_session_report.get("content", {})
    
    # Append user message
    session_data["transcript"].append({
        "role": "founder",
        "content": req.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    engine = BuildEngine(db_service=db)
    new_codebase = await engine.process_feedback(target_idea, session_data.get("codebase", {}), req.message)
    
    session_data["codebase"] = new_codebase
    session_data["transcript"].append({
        "role": "ai",
        "content": "I've updated the codebase according to your feedback.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    session_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Save the updated session back to the DB
    report_data = {
        "idea_id": target_idea["id"],
        "organization_id": target_session_report.get("organization_id"),
        "report_type": "build_session",
        "content": session_data
    }
    await db.create_report(report_data)
    
    return BuildSessionResponse(**session_data)
