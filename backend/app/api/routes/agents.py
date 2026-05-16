"""
Agents API Routes — Agent status and activity monitoring.
"""

import structlog
from fastapi import APIRouter, HTTPException
from app.models.database import get_db_service
from app.models.schemas import AgentActivityResponse

logger = structlog.get_logger()
router = APIRouter()


@router.get("/ideas/{idea_id}/activities", response_model=list[AgentActivityResponse])
async def get_agent_activities(idea_id: str):
    """Get all agent activities for an idea."""
    db = get_db_service()
    activities = await db.get_idea_activities(idea_id)
    return activities


@router.get("/roles")
async def get_available_roles():
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
async def run_single_agent(idea_id: str, agent_role: str):
    """Run a single agent against an idea."""
    from app.agents.crew import get_incubator_crew

    db = get_db_service()
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    valid_roles = ["market_analyst", "tech_architect", "growth_strategist", "financial_analyst", "legal_advisor"]
    if agent_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    try:
        crew = get_incubator_crew()
        output = await crew.run_single_agent(agent_role, idea)
        return {"agent_role": agent_role, "output": output, "status": "completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
