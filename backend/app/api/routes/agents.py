"""
Agents API Routes — Agent status and activity monitoring.
All endpoints require authentication with feature gating.
"""

import structlog
from fastapi import APIRouter, HTTPException, Depends
from app.models.database import get_db_service
from app.models.schemas import AgentActivityResponse
from app.middleware.security import get_current_user, require_feature

logger = structlog.get_logger()
router = APIRouter()


@router.get("/ideas/{idea_id}/activities", response_model=list[AgentActivityResponse])
async def get_agent_activities(idea_id: str, user: dict = Depends(get_current_user)):
    """Get all agent activities for an idea."""
    db = get_db_service()

    # Verify idea ownership or org membership
    idea = await db.get_idea(idea_id)
    if idea and idea.get("user_id") != user["id"] and user.get("platform_role") != "super_admin":
        if not user.get("org_id") or idea.get("organization_id") != user.get("org_id"):
            raise HTTPException(status_code=403, detail="Access denied")

    activities = await db.get_idea_activities(idea_id)
    return activities


@router.get("/roles")
async def get_available_roles(user: dict = Depends(get_current_user)):
    """Get all available agent roles and their descriptions."""
    return {
        "roles": [
            {"id": "market_analyst", "name": "Market Analyst", "description": "Conducts market research, competitor analysis, and TAM/SAM/SOM sizing."},
            {"id": "tech_architect", "name": "Tech Architect", "description": "Designs system architecture, recommends tech stacks, estimates costs."},
            {"id": "growth_strategist", "name": "Growth Strategist", "description": "Creates GTM strategy, pricing models, and acquisition plans."},
            {"id": "financial_analyst", "name": "Financial Analyst", "description": "Builds financial projections, unit economics, and funding strategy."},
            {"id": "legal_advisor", "name": "Legal Advisor", "description": "Analyzes IP landscape, regulatory compliance, and legal risks."},
        ]
    }


@router.post("/ideas/{idea_id}/run/{agent_role}")
async def run_single_agent(
    idea_id: str,
    agent_role: str,
    user: dict = Depends(require_feature("single_agent")),
):
    """Run a single agent against an idea. Requires 'single_agent' feature (free+)."""
    from app.agents.crew import get_incubator_crew

    db = get_db_service()
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Ownership check
    if idea.get("user_id") != user["id"] and user.get("platform_role") != "super_admin":
        if not user.get("org_id") or idea.get("organization_id") != user.get("org_id"):
            raise HTTPException(status_code=403, detail="Access denied to this idea")

    valid_roles = ["market_analyst", "tech_architect", "growth_strategist", "financial_analyst", "legal_advisor"]
    if agent_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    # Track usage
    try:
        from app.services.analytics import get_analytics_service
        analytics = get_analytics_service()
        await analytics.track_event(
            user_id=user["id"],
            event_type="agent_run",
            idea_id=idea_id,
            organization_id=idea.get("organization_id"),
            metadata={"agent_role": agent_role},
        )
    except Exception:
        pass

    try:
        crew = get_incubator_crew()
        output = await crew.run_single_agent(agent_role, idea)
        return {"agent_role": agent_role, "output": output, "status": "completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
