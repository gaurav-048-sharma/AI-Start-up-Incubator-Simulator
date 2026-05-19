"""
Workflows API Routes — Workflow state and graph visualization.
All endpoints require authentication.
"""

import structlog
from fastapi import APIRouter, HTTPException, Depends
from app.models.database import get_db_service
from app.models.schemas import WorkflowStateResponse, WorkflowGraphResponse
from app.workflows.graph import get_graph_structure
from app.middleware.security import get_current_user

logger = structlog.get_logger()
router = APIRouter()


@router.get("/ideas/{idea_id}/state", response_model=WorkflowStateResponse)
async def get_workflow_state(idea_id: str, user: dict = Depends(get_current_user)):
    """Get the current workflow state for an idea."""
    db = get_db_service()
    state = await db.get_workflow_state(idea_id)
    if not state:
        raise HTTPException(status_code=404, detail="No workflow state found for this idea")
    return state


@router.get("/graph", response_model=WorkflowGraphResponse)
async def get_workflow_graph(user: dict = Depends(get_current_user)):
    """Get the workflow graph structure for visualization."""
    structure = get_graph_structure()
    return WorkflowGraphResponse(
        nodes=structure["nodes"],
        edges=structure["edges"],
    )


@router.post("/ideas/{idea_id}/retry")
async def retry_workflow(idea_id: str, user: dict = Depends(get_current_user)):
    """Retry a failed workflow step."""
    db = get_db_service()
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Ownership check
    if idea.get("user_id") != user["id"] and user.get("platform_role") != "super_admin":
        from app.middleware.security import has_permission
        effective_role = user.get("org_role") or user.get("role", "viewer")
        if not has_permission(effective_role, "launch_workflow"):
            raise HTTPException(status_code=403, detail="Access denied")

    if idea.get("status") != "failed":
        raise HTTPException(status_code=400, detail="Can only retry failed workflows")

    await db.update_idea(idea_id, {"status": "researching", "progress": 10})
    return {"message": "Workflow retry initiated", "idea_id": idea_id}
