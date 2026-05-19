"""
Simulation API Routes — Investor pitch simulation management.
All endpoints require authentication, feature gating, and organization scoping.
"""

import structlog
from fastapi import APIRouter, HTTPException, Depends
from app.models.database import get_db_service
from app.models.schemas import SimulationCreate, SimulationResponse, SimulationRespond
from app.simulation.pitch_engine import PitchEngine
from app.middleware.security import (
    get_current_user, 
    require_feature, 
    require_org_context,
    require_permission,
    require_mfa_stepup,
)
from uuid import uuid4
from datetime import datetime, timezone

logger = structlog.get_logger()
router = APIRouter()


@router.post("/ideas/{idea_id}/simulate", response_model=SimulationResponse, status_code=201)
async def start_simulation(
    idea_id: str,
    config: SimulationCreate = None,
    user: dict = Depends(require_mfa_stepup()),
    _org: dict = Depends(require_org_context()),
    _feature: dict = Depends(require_feature("pitch_simulation")),
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
        if idea.get("organization_id") != user.get("org_id"):
             raise HTTPException(status_code=403, detail="Access denied")

    sim_id = str(uuid4())
    org_id = user.get("org_id")
    
    sim_data = {
        "id": sim_id,
        "idea_id": idea_id,
        "organization_id": org_id,
        "status": "active",
        "investor_profile": config.investor_profile if config else "standard",
        "transcript": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Initialize engine and get opening
        engine = PitchEngine(sim_data["investor_profile"])
        opening = await engine.get_opening_question(idea)
        
        sim_data["transcript"].append({
            "role": "investor",
            "content": opening,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        result = await db.create_simulation(sim_data)
        return result or sim_data
    except Exception as e:
        logger.error("Failed to start simulation", error=str(e), idea_id=idea_id)
        raise HTTPException(status_code=500, detail="Failed to initialize simulator")


@router.get("/{sim_id}", response_model=SimulationResponse)
async def get_simulation(
    sim_id: str, 
    user: dict = Depends(get_current_user),
    _org: dict = Depends(require_org_context()),
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
        if sim.get("organization_id") != user.get("org_id"):
             raise HTTPException(status_code=403, detail="Access denied")

    return sim


@router.get("/ideas/{idea_id}/list")
async def list_simulations(
    idea_id: str, 
    user: dict = Depends(get_current_user),
    _org: dict = Depends(require_org_context()),
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
        if idea.get("organization_id") != user.get("org_id"):
             raise HTTPException(status_code=403, detail="Access denied")

    sims = await db.get_idea_simulations(idea_id)
    return {"simulations": sims}
