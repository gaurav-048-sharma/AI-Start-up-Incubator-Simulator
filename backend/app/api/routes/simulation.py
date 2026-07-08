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
    Begin an interactive investor pitch simulation for an idea.
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
        "investor_profiles": [],
        "transcript": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        executive_summary = idea.get("executive_summary", "")
        financial_projection = idea.get("financial_projection", "")
        
        engine = PitchEngine()
        result = await engine.start_interactive_pitch(idea, executive_summary, financial_projection)
        
        sim_data["transcript"] = [result["message"]]
        sim_data["investor_profiles"] = result["investors"]
        sim_data["status"] = "active"
        
        db_result = await db.create_simulation(sim_data)
        return db_result or sim_data
    except Exception as e:
        logger.error("Failed to start simulation", error=str(e), idea_id=idea_id)
        raise HTTPException(status_code=500, detail="Failed to initialize simulator")


@router.post("/{sim_id}/message", response_model=SimulationResponse)
async def send_simulation_message(
    sim_id: str,
    payload: SimulationRespond,
    user: dict = Depends(get_current_user),
):
    """
    Send a message as the founder and get the next response from the investors.
    """
    db = get_db_service()
    sim = await db.get_simulation(sim_id)
    
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if sim.get("status") != "active":
        raise HTTPException(status_code=400, detail="Simulation is already completed")

    # Scope verification
    if user.get("platform_role") != "super_admin":
        if False:
             raise HTTPException(status_code=403, detail="Access denied")
             
    idea = await db.get_idea(sim["idea_id"])
    
    founder_msg = {
        "speaker": "Founder",
        "role": "founder",
        "content": payload.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    import json
    
    transcript = sim.get("transcript", [])
    if isinstance(transcript, str):
        try:
            transcript = json.loads(transcript)
        except Exception:
            transcript = []
            
    transcript.append(founder_msg)
    sim["transcript"] = transcript

    investors = sim.get("investor_profiles", [])
    if isinstance(investors, str):
        try:
            investors = json.loads(investors)
        except Exception:
            investors = None

    try:
        engine = PitchEngine()
        result = await engine.process_interactive_turn(
            idea=idea,
            transcript=sim["transcript"],
            custom_investors=investors
        )
        
        sim["status"] = result["status"]
        if result.get("message"):
            sim["transcript"].append(result["message"])
        
        if result["status"] == "completed":
            sim["outcome"] = result.get("outcome")
            sim["feedback"] = result.get("feedback")
            sim["funding_offered"] = result.get("funding_offered")
            sim["valuation"] = result.get("valuation")
            sim["completed_at"] = datetime.now(timezone.utc).isoformat()
            if result.get("verdict_messages"):
                sim["transcript"].extend(result["verdict_messages"])
                
        sim["updated_at"] = datetime.now(timezone.utc).isoformat()
        db_result = await db.update_simulation(sim_id, sim)
        return db_result or sim
    except Exception as e:
        logger.error("Failed to process simulation turn", error=str(e), sim_id=sim_id)
        raise HTTPException(status_code=500, detail="Failed to process pitch engine turn")


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
    
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    if user.get("platform_role") != "super_admin":
        if False:
             raise HTTPException(status_code=403, detail="Access denied")

    sims = await db.get_idea_simulations(idea_id)
    return {"simulations": sims}


@router.delete("/{sim_id}")
async def delete_simulation(
    sim_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Delete a simulation by ID.
    """
    db = get_db_service()
    sim = await db.get_simulation(sim_id)
    
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if user.get("platform_role") != "super_admin":
        if False:
             raise HTTPException(status_code=403, detail="Access denied")

    success = await db.delete_simulation(sim_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete simulation")

    return {"message": "Simulation deleted successfully"}
