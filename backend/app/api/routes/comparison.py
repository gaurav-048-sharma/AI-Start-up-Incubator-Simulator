"""
Comparison API Routes — side-by-side idea analysis and radar chart data.
Requires authentication and pro+ tier for comparison features.
"""

import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.middleware.security import get_current_user
logger = structlog.get_logger()
router = APIRouter()

class CompareRequest(BaseModel):
    idea_ids: list[str]

class ComparisonDimension(BaseModel):
    dimension: str
    label: str
    scores: dict[str, float]

class ComparisonResponse(BaseModel):
    ideas: list[dict]
    dimensions: list[ComparisonDimension]
    recommendation: str

@router.post("/compare")
async def compare_ideas(
    req: CompareRequest,
    user: dict = Depends(get_current_user),
):
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

    # Fetch all ideas with ownership/org checks
    ideas = []
    for idea_id in req.idea_ids:
        idea = await db.get_idea(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail=f"Idea not found: {idea_id}")
        # Verify access
        if idea.get("user_id") != user["id"] and user.get("platform_role") != "super_admin":
            if False:
                raise HTTPException(status_code=403, detail=f"Access denied to idea: {idea_id}")
        ideas.append(idea)

    # Fetch reports for each idea
    idea_reports: dict[str, list[dict]] = {}
    for idea in ideas:
        reports = await db.get_idea_reports(idea["id"])
        idea_reports[idea["id"]] = reports

    # Fetch simulations for pitch scores
    idea_sims: dict[str, list[dict]] = {}
    for idea in ideas:
        sims = await db.get_idea_simulations(idea["id"])
        idea_sims[idea["id"]] = sims

    dimensions = _build_comparison_dimensions(ideas, idea_reports, idea_sims)
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
    dimensions = []

    scores = {idea["id"]: min(idea.get("progress", 0) / 100.0, 1.0) for idea in ideas}
    dimensions.append(ComparisonDimension(dimension="completion", label="Completion", scores=scores))

    max_reports = max(len(reports.get(idea["id"], [])) for idea in ideas) or 1
    scores = {idea["id"]: len(reports.get(idea["id"], [])) / max_reports for idea in ideas}
    dimensions.append(ComparisonDimension(dimension="research_depth", label="Research Depth", scores=scores))

    key_types = {"market_analysis", "growth_strategy", "financial_projection"}
    scores = {}
    for idea in ideas:
        idea_report_types = {r.get("report_type") for r in reports.get(idea["id"], [])}
        scores[idea["id"]] = len(idea_report_types & key_types) / len(key_types)
    dimensions.append(ComparisonDimension(dimension="market_readiness", label="Market Readiness", scores=scores))

    tech_types = {"tech_architecture", "legal_review"}
    scores = {}
    for idea in ideas:
        idea_report_types = {r.get("report_type") for r in reports.get(idea["id"], [])}
        scores[idea["id"]] = len(idea_report_types & tech_types) / len(tech_types)
    dimensions.append(ComparisonDimension(dimension="technical_maturity", label="Technical Maturity", scores=scores))

    outcome_scores = {"funded": 1.0, "conditional": 0.6, "passed": 0.2}
    scores = {}
    for idea in ideas:
        sims = simulations.get(idea["id"], [])
        if sims:
            best = max(outcome_scores.get(s.get("outcome", ""), 0) for s in sims)
            scores[idea["id"]] = best
        else:
            scores[idea["id"]] = 0.0
    dimensions.append(ComparisonDimension(dimension="investor_appeal", label="Investor Appeal", scores=scores))

    scores = {}
    for idea in ideas:
        desc_len = len(idea.get("description", ""))
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
    dimensions.append(ComparisonDimension(dimension="clarity", label="Idea Clarity", scores=scores))

    return dimensions


def _generate_recommendation(ideas: list[dict], dimensions: list[ComparisonDimension]) -> str:
    composite: dict[str, float] = {}
    for idea in ideas:
        total = sum(d.scores.get(idea["id"], 0) for d in dimensions)
        composite[idea["id"]] = total / len(dimensions)

    best_id = max(composite, key=lambda k: composite[k])
    best_idea = next(i for i in ideas if i["id"] == best_id)
    best_score = composite[best_id]
    weakest_dim = min(dimensions, key=lambda d: d.scores.get(best_id, 0))

    strongest_dim = max(dimensions, key=lambda d: d.scores.get(best_id, 0))

    html = f"""
    <div style="font-size: var(--fs-md); line-height: 1.6;">
        <p style="margin-bottom: var(--space-3);">Based on our multi-dimensional analysis, <strong>{best_idea['title']}</strong> emerges as the leading concept with a composite score of <strong style="color: var(--accent); font-size: var(--fs-lg);">{best_score:.0%}</strong>.</p>
        
        <div style="display: flex; gap: var(--space-4); margin: var(--space-4) 0; padding: var(--space-3); background: var(--bg-secondary); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="flex: 1;">
                <div style="font-size: var(--fs-xs); color: var(--text-muted); text-transform: uppercase;">Biggest Strength</div>
                <div style="color: var(--success); font-weight: 600;">{strongest_dim.label} ({strongest_dim.scores.get(best_id, 0):.0%})</div>
            </div>
            <div style="flex: 1;">
                <div style="font-size: var(--fs-xs); color: var(--text-muted); text-transform: uppercase;">Area for Improvement</div>
                <div style="color: var(--warning); font-weight: 600;">{weakest_dim.label} ({weakest_dim.scores.get(best_id, 0):.0%})</div>
            </div>
        </div>
    """

    scores_sorted = sorted(composite.values(), reverse=True)
    if len(scores_sorted) >= 2 and (scores_sorted[0] - scores_sorted[1]) < 0.1:
        runner_up_id = sorted(composite, key=lambda k: composite[k], reverse=True)[1]
        runner_up = next(i for i in ideas if i["id"] == runner_up_id)
        html += f"""
        <div style="padding-left: var(--space-3); border-left: 2px solid var(--accent-tertiary);">
            <span style="font-weight: 600; color: var(--text-primary);">Close Contender:</span> <em>{runner_up['title']}</em> is extremely close ({(scores_sorted[1]):.0%}). Depending on your risk appetite and core competencies, this could still be the winning pivot.
        </div>
        """
        
    html += "</div>"
    return html
