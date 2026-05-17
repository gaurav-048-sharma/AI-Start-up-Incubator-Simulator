"""
Comparison API Routes — side-by-side idea analysis and radar chart data.
"""

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = structlog.get_logger()
router = APIRouter()


class CompareRequest(BaseModel):
    """Request body for comparing ideas."""
    idea_ids: list[str]  # 2-4 idea IDs


class ComparisonDimension(BaseModel):
    """A single dimension in the comparison radar."""
    dimension: str
    label: str
    scores: dict[str, float]  # idea_id -> score


class ComparisonResponse(BaseModel):
    """Full comparison result."""
    ideas: list[dict]
    dimensions: list[ComparisonDimension]
    recommendation: Optional[str] = None


@router.post("/compare", response_model=ComparisonResponse)
async def compare_ideas(req: CompareRequest):
    """
    Compare 2-4 startup ideas across multiple dimensions.
    Returns radar chart data and a recommendation.
    """
    if len(req.idea_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 ideas are required for comparison")
    if len(req.idea_ids) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 ideas can be compared at once")

    from app.models.database import get_db_service
    db = get_db_service()

    # Fetch all ideas
    ideas = []
    for idea_id in req.idea_ids:
        idea = await db.get_idea(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"Idea not found: {idea_id}")
        ideas.append(idea)

    # Fetch reports for each idea to extract scores
    idea_reports: dict[str, list[dict]] = {}
    for idea in ideas:
        reports = await db.get_idea_reports(idea["id"])
        idea_reports[idea["id"]] = reports

    # Fetch simulations for pitch scores
    idea_sims: dict[str, list[dict]] = {}
    for idea in ideas:
        sims = await db.get_idea_simulations(idea["id"])
        idea_sims[idea["id"]] = sims

    # Build dimension scores
    dimensions = _build_comparison_dimensions(ideas, idea_reports, idea_sims)

    # Generate recommendation
    recommendation = _generate_recommendation(ideas, dimensions)

    return ComparisonResponse(
        ideas=[{
            "id": idea["id"],
            "title": idea["title"],
            "industry": idea.get("industry"),
            "status": idea.get("status"),
            "progress": idea.get("progress", 0),
        } for idea in ideas],
        dimensions=dimensions,
        recommendation=recommendation,
    )


def _build_comparison_dimensions(
    ideas: list[dict],
    reports: dict[str, list[dict]],
    simulations: dict[str, list[dict]],
) -> list[ComparisonDimension]:
    """
    Build comparison dimensions from available data.
    Uses heuristic scoring when detailed AI scores aren't available.
    """
    dimensions = []

    # 1. Completion Progress
    scores = {idea["id"]: min(idea.get("progress", 0) / 100.0, 1.0) for idea in ideas}
    dimensions.append(ComparisonDimension(
        dimension="completion", label="Completion", scores=scores,
    ))

    # 2. Research Depth (based on number of reports)
    max_reports = max(len(reports.get(idea["id"], [])) for idea in ideas) or 1
    scores = {idea["id"]: len(reports.get(idea["id"], [])) / max_reports for idea in ideas}
    dimensions.append(ComparisonDimension(
        dimension="research_depth", label="Research Depth", scores=scores,
    ))

    # 3. Market Readiness (based on whether key reports exist)
    key_types = {"market_analysis", "growth_strategy", "financial_projection"}
    scores = {}
    for idea in ideas:
        idea_report_types = {r.get("report_type") for r in reports.get(idea["id"], [])}
        scores[idea["id"]] = len(idea_report_types & key_types) / len(key_types)
    dimensions.append(ComparisonDimension(
        dimension="market_readiness", label="Market Readiness", scores=scores,
    ))

    # 4. Technical Maturity (has tech architecture + legal)
    tech_types = {"tech_architecture", "legal_review"}
    scores = {}
    for idea in ideas:
        idea_report_types = {r.get("report_type") for r in reports.get(idea["id"], [])}
        scores[idea["id"]] = len(idea_report_types & tech_types) / len(tech_types)
    dimensions.append(ComparisonDimension(
        dimension="technical_maturity", label="Technical Maturity", scores=scores,
    ))

    # 5. Investor Appeal (based on simulation outcomes)
    outcome_scores = {"funded": 1.0, "conditional": 0.6, "passed": 0.2}
    scores = {}
    for idea in ideas:
        sims = simulations.get(idea["id"], [])
        if sims:
            best = max(outcome_scores.get(s.get("outcome", ""), 0) for s in sims)
            scores[idea["id"]] = best
        else:
            scores[idea["id"]] = 0.0
    dimensions.append(ComparisonDimension(
        dimension="investor_appeal", label="Investor Appeal", scores=scores,
    ))

    # 6. Description Quality (proxy: description length vs. optimal ~500 chars)
    scores = {}
    for idea in ideas:
        desc_len = len(idea.get("description", ""))
        # Score peaks at ~500 chars, diminishes for very short or very long
        if desc_len < 50:
            scores[idea["id"]] = 0.2
        elif desc_len < 200:
            scores[idea["id"]] = 0.5
        elif desc_len < 800:
            scores[idea["id"]] = 1.0
        elif desc_len < 2000:
            scores[idea["id"]] = 0.8
        else:
            scores[idea["id"]] = 0.6
    dimensions.append(ComparisonDimension(
        dimension="clarity", label="Idea Clarity", scores=scores,
    ))

    return dimensions


def _generate_recommendation(
    ideas: list[dict], dimensions: list[ComparisonDimension]
) -> str:
    """Generate a text recommendation based on dimension scores."""
    # Calculate composite score for each idea
    composite: dict[str, float] = {}
    for idea in ideas:
        total = sum(d.scores.get(idea["id"], 0) for d in dimensions)
        composite[idea["id"]] = total / len(dimensions)

    # Find best idea
    best_id = max(composite, key=lambda k: composite[k])
    best_idea = next(i for i in ideas if i["id"] == best_id)
    best_score = composite[best_id]

    # Find weaknesses of best idea
    weakest_dim = min(dimensions, key=lambda d: d.scores.get(best_id, 0))

    recommendation = (
        f'"{best_idea["title"]}" leads with a composite score of {best_score:.0%}. '
        f'Its weakest area is {weakest_dim.label} ({weakest_dim.scores.get(best_id, 0):.0%}). '
    )

    # If scores are close, mention it
    scores_sorted = sorted(composite.values(), reverse=True)
    if len(scores_sorted) >= 2 and (scores_sorted[0] - scores_sorted[1]) < 0.1:
        runner_up_id = sorted(composite, key=lambda k: composite[k], reverse=True)[1]
        runner_up = next(i for i in ideas if i["id"] == runner_up_id)
        recommendation += f'However, "{runner_up["title"]}" is very close — consider the specific dimensions that matter most to your goals.'

    return recommendation
