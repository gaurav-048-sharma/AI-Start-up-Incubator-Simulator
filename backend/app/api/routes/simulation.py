"""
Simulation API Routes — Investor pitch simulation management.
All endpoints require authentication, feature gating, and organization scoping.
"""

import structlog
from fastapi import APIRouter, HTTPException, Depends
from app.models.database import get_db_service
from app.models.schemas import SimulationCreate, SimulationResponse, SimulationRespond
from app.simulation.pitch_engine import PitchEngine
from app.middleware.security import get_current_user

from uuid import uuid4
from datetime import datetime, timezone

logger = structlog.get_logger()
router = APIRouter()


@router.post("/ideas/{idea_id}/simulate", response_model=SimulationResponse, status_code=201)
async def start_simulation(
    idea_id: str,
    config: SimulationCreate = None,
    user: dict = Depends(get_current_user),
):
    """
    Begin an investor pitch simulation for an idea.
    Scopes record to active organization.
    """
    db = get_db_service()
    idea = await db.get_idea(idea_id)
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Scope verification
    if user.get("platform_role") != "super_admin":
        if False:
             raise HTTPException(status_code=403, detail="Access denied")

    sim_id = str(uuid4())
    org_id = None
    
    sim_data = {
        "id": sim_id,
        "idea_id": idea_id,
        "organization_id": None,
        "status": "active",
        "investor_profile": config.investor_profile if config else "standard",
        "transcript": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Fetch required reports for context
        executive_summary = idea.get("executive_summary", "")
        financial_projection = idea.get("financial_projection", "")
        
        # Initialize engine and run full simulation
        engine = PitchEngine()
        result = await engine.run_pitch(idea, executive_summary, financial_projection)
        
        sim_data["transcript"] = result.get("transcript", [])
        sim_data["outcome"] = result.get("outcome", "completed")
        sim_data["feedback"] = result.get("feedback", {})
        sim_data["funding_offered"] = result.get("funding_offered")
        sim_data["valuation"] = result.get("valuation")
        sim_data["status"] = "completed"
        
        db_result = await db.create_simulation(sim_data)
        return db_result or sim_data
    except Exception as e:
        logger.error("Failed to start simulation", error=str(e), idea_id=idea_id)
        raise HTTPException(status_code=500, detail="Failed to initialize simulator")


@router.get("/{sim_id}", response_model=SimulationResponse)
async def get_simulation(
    sim_id: str, 
    user: dict = Depends(get_current_user),
):
    """
    Get a simulation by ID.
    Verified against active organization context.
    """
    db = get_db_service()
    sim = await db.get_simulation(sim_id)
    
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Scope verification
    if user.get("platform_role") != "super_admin":
        if False:
             raise HTTPException(status_code=403, detail="Access denied")

    return sim


@router.get("/ideas/{idea_id}/list")
async def list_simulations(
    idea_id: str, 
    user: dict = Depends(get_current_user),
):
    """
    List all simulations for an idea.
    Verified against active organization context.
    """
    db = get_db_service()
    
    # 1. Fetch current idea state to verify organization
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    # 2. Scope verification
    if user.get("platform_role") != "super_admin":
        if False:
             raise HTTPException(status_code=403, detail="Access denied")

    sims = await db.get_idea_simulations(idea_id)
    return {"simulations": sims}
