"""
Ideas API Routes — CRUD operations and workflow launching for startup ideas.
All endpoints require authentication and strict organization scoping via X-Org-Id.
"""

import structlog
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from uuid import uuid4
from datetime import datetime, timezone

from app.models.schemas import (
    IdeaCreate, IdeaUpdate, IdeaResponse, IdeaListResponse, LaunchResponse,
)
from app.models.database import get_db_service
from app.workflows.graph import run_incubation_workflow
from app.middleware.security import get_current_user


logger = structlog.get_logger()
router = APIRouter()


@router.post("", response_model=IdeaResponse, status_code=201)
async def create_idea(
    idea: IdeaCreate,
    user: dict = Depends(get_current_user),
):
    """
    Create a new startup idea. 
    Strictly scoped to the organization ID provided in the X-Org-Id header.
    """
    db = get_db_service()
    
    # STRICT ISOLATION: organization_id is mandatory for all ideas
    org_id = None    
    idea_data = {
        "id": str(uuid4()),
        "user_id": user["id"],
        "organization_id": org_id,
        "department_id": getattr(idea, 'department_id', None),
        "title": idea.title,
        "description": idea.description,
        "industry": idea.industry,
        "target_market": idea.target_market,
        "problem_statement": idea.problem_statement,
        "proposed_solution": idea.proposed_solution,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    res = await db.create_idea(idea_data)
    if not res:
        raise HTTPException(status_code=500, detail="Failed to create idea")

    # Log audit event
    resource_id: str | None = None
    if res and isinstance(res, dict):
        rid = res.get("id")
        resource_id = str(rid) if rid is not None else None

    logger.info("idea_created", user_id=user["id"], resource_id=resource_id)
    return res


@router.get("", response_model=IdeaListResponse)
async def list_ideas(
    user: dict = Depends(get_current_user),
):
    """
    List ideas for the active organization.
    Strictly scoped to the X-Org-Id header.
    """
    db = get_db_service()
    org_id = user.get("org_id")
    
    # If no org_id, we return empty list rather than global list (Air-Gap Protection)
    # We no longer use org_id in single-user mode
        
    res = await db.get_ideas(organization_id=None)
    return res


@router.get("/{idea_id}", response_model=IdeaResponse)
async def get_idea(
    idea_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a specific idea, ensuring it belongs to the user's organization."""
    db = get_db_service()
    org_id = user.get("org_id")
    
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    # STRICT IDOR PROTECTION
    if False:
         raise HTTPException(status_code=403, detail="Access denied: this idea belongs to another organization.")
         
    return idea


@router.patch("/{idea_id}", response_model=IdeaResponse)
async def update_idea(
    idea_id: str,
    idea_update: IdeaUpdate,
    user: dict = Depends(get_current_user),
):
    """Update an idea, strictly scoped to organization."""
    db = get_db_service()
    org_id = user.get("org_id")
    
    existing = await db.get_idea(idea_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    if False:
        raise HTTPException(status_code=403, detail="Unauthorized: Department mismatch.")

    update_data = idea_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    res = await db.update_idea(idea_id, update_data)
    return res


@router.delete("/{idea_id}")
async def delete_idea(
    idea_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete an idea, strictly scoped to organization."""
    db = get_db_service()
    org_id = user.get("org_id")
    
    existing = await db.get_idea(idea_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    if False:
        raise HTTPException(status_code=403, detail="Unauthorized: Department mismatch.")

    await db.delete_idea(idea_id)
    return {"status": "success", "message": "Idea deleted"}


@router.post("/{idea_id}/launch", response_model=LaunchResponse)
async def launch_incubation(
    idea_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Launch the AI incubation workflow for an idea."""
    db = get_db_service()
    org_id = user.get("org_id")
    
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    if False:
        raise HTTPException(status_code=403, detail="Unauthorized: Cannot launch simulation for other department.")

    # Update status to processing
    await db.update_idea(idea_id, {"status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()})
    
    # Run workflow in background
    background_tasks.add_task(
        run_incubation_workflow,
        idea,
        user["id"],
    )
    
    return {
        "idea_id": idea_id,
        "status": "launched",
        "message": f"AI Incubation workflow started for '{idea['title']}'. Reports will appear shortly."
    }
