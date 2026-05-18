"""
LangGraph Workflow Nodes — Defines the processing nodes in the incubation workflow.
Each node reads from the state, performs work, and returns state updates.
"""

import structlog
from datetime import datetime, timezone

from app.workflows.state import IncubatorState
from app.agents.crew import get_incubator_crew
from app.services.llm import get_llm_service

logger = structlog.get_logger()


async def research_node(state: IncubatorState) -> dict:
    """
    RESEARCH NODE — Runs Market Analyst and Tech Architect.
    First phase of the incubation workflow.
    """
    idea = state["idea"]
    logger.info("Research node started", idea_title=idea.get("title"))

    try:
        crew = get_incubator_crew()

        # Run market research
        market_output = await crew.run_single_agent("market_analyst", idea)

        # Run tech architecture (can use market research for context)
        tech_output = await crew.run_single_agent("tech_architect", idea)

        return {
            "market_research": market_output,
            "tech_architecture": tech_output,
            "current_phase": "validate",
            "messages": [f"[{_timestamp()}] Research phase completed — market analysis and tech architecture generated."],
        }
    except Exception as e:
        logger.error("Research node failed", error=str(e))
        return {
            "errors": [f"Research failed: {str(e)}"],
            "current_phase": "validate",
            "messages": [f"[{_timestamp()}] Research phase encountered errors: {str(e)}"],
        }


async def validate_node(state: IncubatorState) -> dict:
    """
    VALIDATE NODE — Quality gate that evaluates research outputs.
    Assigns quality scores and determines if re-research is needed.
    """
    logger.info("Validate node started")

    try:
        llm_service = get_llm_service()

        # Build validation prompt
        validation_prompt = (
            "You are a quality assurance reviewer for startup research reports. "
            "Evaluate the following research outputs and assign a quality score from 0.0 to 1.0 "
            "for each section. A score above 0.7 means the section is good enough to proceed.\n\n"
            f"## Market Research:\n{state.get('market_research', 'Not completed')[:3000]}\n\n"
            f"## Tech Architecture:\n{state.get('tech_architecture', 'Not completed')[:3000]}\n\n"
            "Respond in this exact format:\n"
            "MARKET_SCORE: <0.0-1.0>\n"
            "TECH_SCORE: <0.0-1.0>\n"
            "OVERALL_SCORE: <0.0-1.0>\n"
            "FEEDBACK: <specific feedback for improvement>\n"
        )

        response = await llm_service.generate(validation_prompt)

        # Parse scores from response
        scores = _parse_quality_scores(response)
        overall = scores.get("overall", 0.5)

        return {
            "quality_scores": scores,
            "overall_quality": overall,
            "quality_feedback": [response],
            "current_phase": "plan",
            "messages": [f"[{_timestamp()}] Validation complete — overall quality: {overall:.2f}"],
            "decisions": [{
                "node": "validate",
                "decision": "proceed" if overall >= 0.7 else "needs_improvement",
                "score": overall,
                "timestamp": _timestamp(),
            }],
        }
    except Exception as e:
        logger.error("Validate node failed", error=str(e))
        return {
            "overall_quality": 0.5,
            "current_phase": "plan",
            "errors": [f"Validation failed: {str(e)}"],
            "messages": [f"[{_timestamp()}] Validation skipped due to error, proceeding."],
        }


async def plan_node(state: IncubatorState) -> dict:
    """
    PLAN NODE — Runs Growth Strategist and Financial Analyst.
    Uses market research context for informed planning.
    """
    idea = state["idea"]
    logger.info("Plan node started", idea_title=idea.get("title"))

    try:
        crew = get_incubator_crew()

        # Run growth strategy
        growth_output = await crew.run_single_agent("growth_strategist", idea)

        # Run financial analysis
        financial_output = await crew.run_single_agent("financial_analyst", idea)

        # Run legal review
        legal_output = await crew.run_single_agent("legal_advisor", idea)

        return {
            "growth_strategy": growth_output,
            "financial_projection": financial_output,
            "legal_review": legal_output,
            "current_phase": "build",
            "messages": [f"[{_timestamp()}] Planning phase completed — growth, financial, and legal analysis generated."],
        }
    except Exception as e:
        logger.error("Plan node failed", error=str(e))
        return {
            "errors": [f"Planning failed: {str(e)}"],
            "current_phase": "build",
            "messages": [f"[{_timestamp()}] Planning phase encountered errors: {str(e)}"],
        }


async def build_node(state: IncubatorState) -> dict:
    """
    BUILD NODE — Generates executive summary and pitch deck content.
    Synthesizes all agent outputs into investor-ready materials.
    """
    logger.info("Build node started")

    try:
        llm_service = get_llm_service()

        # Generate executive summary
        summary_prompt = (
            "You are a startup pitch expert. Based on the following research and analysis, "
            "create a compelling executive summary (2-3 pages) that an investor can read in 5 minutes.\n\n"
            f"## Startup Idea:\n{_format_idea(state['idea'])}\n\n"
            f"## Market Research:\n{state.get('market_research', 'N/A')[:2000]}\n\n"
            f"## Tech Architecture:\n{state.get('tech_architecture', 'N/A')[:2000]}\n\n"
            f"## Growth Strategy:\n{state.get('growth_strategy', 'N/A')[:2000]}\n\n"
            f"## Financial Projections:\n{state.get('financial_projection', 'N/A')[:2000]}\n\n"
            f"## Legal Review:\n{state.get('legal_review', 'N/A')[:1000]}\n\n"
            "Create an executive summary with these sections:\n"
            "1. The Problem & Opportunity\n"
            "2. Our Solution\n"
            "3. Market Opportunity (TAM/SAM/SOM)\n"
            "4. Business Model & Unit Economics\n"
            "5. Competitive Advantage\n"
            "6. Go-to-Market Strategy\n"
            "7. Financial Highlights\n"
            "8. The Ask (funding amount and use of funds)\n"
        )

        executive_summary = await llm_service.generate(summary_prompt)

        # Generate pitch deck content
        pitch_prompt = (
            "Based on all the research above, create a 12-slide pitch deck outline "
            "with specific content for each slide. Format as:\n"
            "SLIDE 1: [Title] - [Content]\n"
            "SLIDE 2: [Title] - [Content]\n"
            "... etc.\n\n"
            f"Context:\n{executive_summary[:3000]}\n"
        )

        pitch_deck = await llm_service.generate(pitch_prompt)

        # Build report metadata
        reports = [
            {"type": "market_research", "title": "Market Research Report", "status": "completed"},
            {"type": "tech_architecture", "title": "Technical Architecture", "status": "completed"},
            {"type": "growth_strategy", "title": "Growth Strategy", "status": "completed"},
            {"type": "financial_projection", "title": "Financial Projections", "status": "completed"},
            {"type": "legal_review", "title": "Legal & IP Review", "status": "completed"},
            {"type": "executive_summary", "title": "Executive Summary", "status": "completed"},
            {"type": "pitch_deck_content", "title": "Pitch Deck", "status": "completed"},
        ]

        return {
            "executive_summary": executive_summary,
            "pitch_deck_content": pitch_deck,
            "reports": reports,
            "current_phase": "simulate",
            "messages": [f"[{_timestamp()}] Build phase completed — executive summary and pitch deck generated."],
        }
    except Exception as e:
        logger.error("Build node failed", error=str(e))
        return {
            "errors": [f"Build failed: {str(e)}"],
            "current_phase": "simulate",
            "messages": [f"[{_timestamp()}] Build phase encountered errors: {str(e)}"],
        }


async def simulate_node(state: IncubatorState) -> dict:
    """
    SIMULATE NODE — Runs investor pitch simulation using AutoGen.
    Founder agent pitches to investor agents.
    """
    logger.info("Simulate node started")

    try:
        from app.simulation.pitch_engine import PitchEngine

        engine = PitchEngine()
        result = await engine.run_pitch(
            idea=state["idea"],
            executive_summary=state.get("executive_summary", ""),
            financial_projection=state.get("financial_projection", ""),
        )

        return {
            "simulation_transcript": result.get("transcript", []),
            "simulation_outcome": result.get("outcome", "undetermined"),
            "investor_feedback": result.get("feedback", {}),
            "funding_offered": result.get("funding_offered"),
            "valuation": result.get("valuation"),
            "current_phase": "completed",
            "status": "completed",
            "messages": [f"[{_timestamp()}] Simulation completed — outcome: {result.get('outcome', 'N/A')}"],
        }
    except Exception as e:
        logger.error("Simulate node failed", error=str(e))
        return {
            "current_phase": "completed",
            "status": "completed",
            "errors": [f"Simulation failed: {str(e)}"],
            "messages": [f"[{_timestamp()}] Simulation skipped due to error. Incubation otherwise complete."],
        }


async def error_handler_node(state: IncubatorState) -> dict:
    """Handle workflow errors gracefully."""
    logger.warning("Error handler triggered", errors=state.get("errors", []))
    return {
        "status": "failed",
        "messages": [f"[{_timestamp()}] Workflow encountered unrecoverable errors."],
    }


# ── Helper Functions ──────────────────────────────────────────────

def _timestamp() -> str:
    """Get current UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_idea(idea: dict) -> str:
    """Format idea dict for prompts."""
    return (
        f"**Title:** {idea.get('title', 'N/A')}\n"
        f"**Description:** {idea.get('description', 'N/A')}\n"
        f"**Industry:** {idea.get('industry', 'N/A')}\n"
        f"**Target Market:** {idea.get('target_market', 'N/A')}\n"
        f"**Problem:** {idea.get('problem_statement', 'N/A')}\n"
        f"**Solution:** {idea.get('proposed_solution', 'N/A')}\n"
    )


def _parse_quality_scores(response: str) -> dict:
    """Parse quality scores from LLM validation response."""
    scores = {}
    try:
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("MARKET_SCORE:"):
                scores["market"] = float(line.split(":")[1].strip())
            elif line.startswith("TECH_SCORE:"):
                scores["tech"] = float(line.split(":")[1].strip())
            elif line.startswith("OVERALL_SCORE:"):
                scores["overall"] = float(line.split(":")[1].strip())
    except (ValueError, IndexError):
        scores["overall"] = 0.5  # Default if parsing fails

    if "overall" not in scores:
        # Calculate from components if overall not parsed
        component_scores = [v for k, v in scores.items() if k != "overall"]
        scores["overall"] = sum(component_scores) / len(component_scores) if component_scores else 0.5

    return scores
