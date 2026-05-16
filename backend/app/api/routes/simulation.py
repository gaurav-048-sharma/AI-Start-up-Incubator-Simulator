"""
Simulation API Routes — Investor pitch simulation management.
"""

import structlog
from fastapi import APIRouter, HTTPException
from app.models.database import get_db_service
from app.models.schemas import SimulationCreate, SimulationResponse, SimulationRespond
from app.simulation.pitch_engine import PitchEngine
from uuid import uuid4
from datetime import datetime, timezone

logger = structlog.get_logger()
router = APIRouter()


@router.post("/ideas/{idea_id}/simulate", response_model=SimulationResponse, status_code=201)
async def start_simulation(idea_id: str, config: SimulationCreate = None):
    """Start an investor pitch simulation for an idea."""
    db = get_db_service()
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Get existing reports for context
    reports = await db.get_idea_reports(idea_id)
    exec_summary = ""
    financial = ""
    for r in reports:
        if r.get("report_type") == "executive_summary":
            exec_summary = r.get("content", {}).get("raw", "")
        elif r.get("report_type") == "financial_projection":
            financial = r.get("content", {}).get("raw", "")

    engine = PitchEngine()
    result = await engine.run_pitch(
        idea=idea,
        executive_summary=exec_summary,
        financial_projection=financial,
    )

    sim_data = {
        "id": str(uuid4()),
        "idea_id": idea_id,
        "simulation_type": config.simulation_type if config else "pitch",
        "investor_profiles": result.get("feedback", {}),
        "transcript": result.get("transcript", []),
        "outcome": result.get("outcome"),
        "funding_offered": result.get("funding_offered"),
        "valuation": result.get("valuation"),
        "feedback": result.get("feedback"),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.create_simulation(sim_data)
    return sim_data


@router.get("/{sim_id}", response_model=SimulationResponse)
async def get_simulation(sim_id: str):
    """Get a simulation by ID."""
    db = get_db_service()
    sim = await db.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


@router.get("/ideas/{idea_id}/list")
async def list_simulations(idea_id: str):
    """List all simulations for an idea."""
    db = get_db_service()
    sims = await db.get_idea_simulations(idea_id)
    return {"simulations": sims, "total": len(sims)}
