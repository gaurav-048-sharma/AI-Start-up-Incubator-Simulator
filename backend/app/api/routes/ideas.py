"""
Ideas API Routes — CRUD operations and workflow launching for startup ideas.
"""

import structlog
from fastapi import APIRouter, HTTPException, BackgroundTasks
from uuid import uuid4
from datetime import datetime, timezone

from app.models.schemas import (
    IdeaCreate, IdeaUpdate, IdeaResponse, IdeaListResponse, LaunchResponse,
)
from app.models.database import get_db_service
from app.workflows.graph import run_incubation_workflow
from app.middleware.security import get_current_user
from fastapi import Depends

logger = structlog.get_logger()
router = APIRouter()


@router.post("", response_model=IdeaResponse, status_code=201)
async def create_idea(idea: IdeaCreate, user: dict = Depends(get_current_user)):
    """Create a new startup idea."""
    db = get_db_service()
    idea_data = {
        "id": str(uuid4()),
        "user_id": user["id"],
        "title": idea.title,
        "description": idea.description,
        "industry": idea.industry,
        "target_market": idea.target_market,
        "problem_statement": idea.problem_statement,
        "proposed_solution": idea.proposed_solution,
        "status": "draft",
        "progress": 0,
        "metadata": idea.metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result = await db.create_idea(idea_data)
        if result:
            return result
        # Fallback for when DB is not connected
        return idea_data
    except Exception as e:
        logger.error("Failed to create idea", error=str(e))
        return idea_data


@router.get("", response_model=IdeaListResponse)
async def list_ideas(user: dict = Depends(get_current_user)):
    """List all ideas for a user."""
    db = get_db_service()
    try:
        ideas = await db.get_user_ideas(user["id"])
        return {"ideas": ideas, "total": len(ideas)}
    except Exception:
        return {"ideas": [], "total": 0}


@router.get("/{idea_id}", response_model=IdeaResponse)
async def get_idea(idea_id: str):
    """Get a specific idea by ID."""
    db = get_db_service()
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.put("/{idea_id}", response_model=IdeaResponse)
async def update_idea(idea_id: str, update: IdeaUpdate):
    """Update a startup idea."""
    db = get_db_service()
    update_data = update.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.update_idea(idea_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Idea not found")
    return result


@router.delete("/{idea_id}", status_code=204)
async def delete_idea(idea_id: str):
    """Delete a startup idea."""
    db = get_db_service()
    deleted = await db.delete_idea(idea_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Idea not found")


@router.post("/{idea_id}/launch", response_model=LaunchResponse)
async def launch_incubation(idea_id: str, background_tasks: BackgroundTasks):
    """Launch the full incubation workflow for an idea."""
    db = get_db_service()
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Update status to submitted
    await db.update_idea(idea_id, {"status": "submitted", "progress": 5})

    # Run workflow in background
    background_tasks.add_task(_run_workflow_background, idea, idea_id)

    return LaunchResponse(
        idea_id=idea_id,
        status="launched",
        message="Incubation workflow started. Monitor progress via WebSocket or agent activity endpoints.",
    )


async def _run_workflow_background(idea: dict, idea_id: str):
    """Background task to run the full incubation workflow."""
    db = get_db_service()
    user_id = idea.get("user_id", "demo-user")

    # Track usage event
    try:
        from app.services.analytics import get_analytics_service
        analytics = get_analytics_service()
        await analytics.track_event(
            user_id=user_id,
            event_type="workflow_run",
            idea_id=idea_id,
            metadata={"idea_title": idea.get("title", "")},
        )
    except Exception as e:
        logger.warning("Analytics tracking skipped", error=str(e))

    try:
        await db.update_idea(idea_id, {"status": "researching", "progress": 10})
        result = await run_incubation_workflow(idea, user_id)

        # Save reports
        for report in result.get("reports", []):
            report_data = {
                "idea_id": idea_id,
                "report_type": report["type"],
                "title": report["title"],
                "content": {"raw": result.get(report["type"], "")},
            }
            await db.create_report(report_data)

        final_status = result.get("status", "completed")
        await db.update_idea(idea_id, {
            "status": final_status,
            "progress": 100,
            "current_phase": result.get("current_phase", "completed"),
        })

        # Send completion notification
        try:
            from app.services.notifications import get_notification_service
            notif = get_notification_service()
            await notif.notify_workflow_complete(
                user_id=user_id,
                idea_id=idea_id,
                idea_title=idea.get("title", "Untitled"),
                status=final_status,
            )

            # Check if credits are low after deduction
            from app.services.analytics import get_analytics_service
            analytics = get_analytics_service()
            remaining = await analytics.get_user_credits(user_id)
            await notif.notify_credits_low(user_id, remaining)
        except Exception as e:
            logger.warning("Notification dispatch skipped", error=str(e))

        logger.info("Background workflow completed", idea_id=idea_id)
    except Exception as e:
        logger.error("Background workflow failed", idea_id=idea_id, error=str(e))
        await db.update_idea(idea_id, {"status": "failed", "progress": 0})

        # Notify about failure
        try:
            from app.services.notifications import get_notification_service
            notif = get_notification_service()
            await notif.notify_workflow_complete(
                user_id=user_id,
                idea_id=idea_id,
                idea_title=idea.get("title", "Untitled"),
                status="failed",
            )
        except Exception:
            pass

