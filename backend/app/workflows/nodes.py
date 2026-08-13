"""
LangGraph Workflow Nodes — Defines the processing nodes in the incubation workflow.
Each node reads from the state, performs work, and returns state updates.

Every node now streams granular events to the EventBus (app.services.events):
  phase   — node lifecycle (started / completed)
  agent   — per-agent status (thinking / complete / error) for the live dashboard
  log     — human-readable terminal lines
  quality — quality-gate verdicts
  sim     — investor pitch transcript turns

Publishing is fire-and-forget into bounded queues, so a slow (or absent)
WebSocket client can never block agent execution.
"""

import time
import structlog
from datetime import datetime, timezone

from app.config import get_settings
from app.workflows.state import IncubatorState
from app.agents.crew import get_incubator_crew
from app.services.llm import get_llm_service
from app.services.events import bus

logger = structlog.get_logger()

AGENT_NAMES = {
    "market_analyst": "Market Analyst",
    "tech_architect": "Tech Architect",
    "product_manager": "Product Manager",
    "growth_strategist": "Growth Strategist",
    "financial_analyst": "Financial Analyst",
    "operations_manager": "Operations Manager",
    "legal_advisor": "Legal Advisor",
}


def _idea_id(state: IncubatorState) -> str:
    return state.get("idea_id") or state.get("idea", {}).get("id", "")


async def _run_agent_streamed(idea_id: str, role: str, idea: dict) -> str:
    """Run one agent while streaming its lifecycle to the dashboard."""
    crew = get_incubator_crew()
    name = AGENT_NAMES.get(role, role)

    await bus.publish(idea_id, "agent", {"agent": role, "status": "thinking"})
    await bus.publish(idea_id, "log", {"agent": role, "level": "info", "message": f"{name} engaged"})

    t0 = time.perf_counter()
    try:
        output = await crew.run_single_agent(role, idea)
    except Exception as exc:
        await bus.publish(idea_id, "agent", {"agent": role, "status": "error", "detail": str(exc)[:200]})
        await bus.publish(idea_id, "log", {"agent": role, "level": "error", "message": f"{name} failed — {exc}"})
        raise

    duration_ms = int((time.perf_counter() - t0) * 1000)
    await bus.publish(idea_id, "agent", {"agent": role, "status": "complete", "duration_ms": duration_ms})
    await bus.publish(idea_id, "log", {
        "agent": role, "level": "success",
        "message": f"{name} delivered {len(output):,} chars in {duration_ms / 1000:.1f}s",
    })
    return output


async def research_node(state: IncubatorState) -> dict:
    """
    RESEARCH NODE — Runs Market Analyst, Tech Architect, and Product Manager.
    First phase of the incubation workflow.
    """
    idea = state["idea"]
    idea_id = _idea_id(state)
    iteration = state.get("iteration", 0) + 1
    logger.info("Research node started", idea_title=idea.get("title"), iteration=iteration)

    await bus.publish(idea_id, "phase", {"phase": "research", "status": "started", "iteration": iteration})

    try:
        market_output = await _run_agent_streamed(idea_id, "market_analyst", idea)
        tech_output = await _run_agent_streamed(idea_id, "tech_architect", idea)
        product_output = await _run_agent_streamed(idea_id, "product_manager", idea)

        await bus.publish(idea_id, "phase", {"phase": "research", "status": "completed", "iteration": iteration})

        return {
            "market_research": market_output,
            "tech_architecture": tech_output,
            "product_spec": product_output,
            "iteration": 1,  # operator.add reducer — counts research passes for the quality-gate loop
            "current_phase": "validate",
            "messages": [f"[{_timestamp()}] Research pass {iteration} completed — market analysis, tech architecture, and product spec generated."],
        }
    except Exception as e:
        logger.error("Research node failed", error=str(e))
        await bus.publish(idea_id, "log", {"level": "error", "message": f"Research phase error: {e}"})
        return {
            "errors": [f"Research failed: {str(e)}"],
            "iteration": 1,
            "current_phase": "validate",
            "messages": [f"[{_timestamp()}] Research phase encountered errors: {str(e)}"],
        }


async def validate_node(state: IncubatorState) -> dict:
    """
    VALIDATE NODE — Quality gate that evaluates research outputs.
    Assigns quality scores and determines if re-research is needed.
    """
    logger.info("Validate node started")
    idea_id = _idea_id(state)
    settings = get_settings()

    await bus.publish(idea_id, "phase", {"phase": "validate", "status": "started"})
    await bus.publish(idea_id, "log", {"level": "info", "message": "Quality gate — scoring research outputs"})

    try:
        llm_service = get_llm_service()

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

        scores = _parse_quality_scores(response)
        overall = scores.get("overall", 0.5)
        passed = overall >= settings.quality_threshold

        await bus.publish(idea_id, "quality", {
            "score": overall,
            "threshold": settings.quality_threshold,
            "passed": passed,
            "iteration": state.get("iteration", 0),
            "scores": scores,
        })
        await bus.publish(idea_id, "log", {
            "level": "success" if passed else "warn",
            "message": (
                f"Quality gate {'PASSED' if passed else 'FAILED'} — "
                f"{overall:.2f} vs threshold {settings.quality_threshold:.2f}"
                + ("" if passed else " — looping back to research")
            ),
        })
        await bus.publish(idea_id, "phase", {"phase": "validate", "status": "completed"})

        return {
            "quality_scores": scores,
            "overall_quality": overall,
            "quality_feedback": [response],
            "current_phase": "plan",
            "messages": [f"[{_timestamp()}] Validation complete — overall quality: {overall:.2f}"],
            "decisions": [{
                "node": "validate",
                "decision": "proceed" if passed else "needs_improvement",
                "score": overall,
                "timestamp": _timestamp(),
            }],
        }
    except Exception as e:
        logger.error("Validate node failed", error=str(e))
        await bus.publish(idea_id, "log", {"level": "warn", "message": f"Validation skipped due to error: {e}"})
        return {
            "overall_quality": 0.5,
            "current_phase": "plan",
            "errors": [f"Validation failed: {str(e)}"],
            "messages": [f"[{_timestamp()}] Validation skipped due to error, proceeding."],
        }


async def plan_node(state: IncubatorState) -> dict:
    """
    PLAN NODE — Runs Growth Strategist, Financial Analyst, Legal Advisor,
    and Operations Manager, using research context for informed planning.
    """
    idea = state["idea"]
    idea_id = _idea_id(state)
    logger.info("Plan node started", idea_title=idea.get("title"))

    await bus.publish(idea_id, "phase", {"phase": "plan", "status": "started"})

    try:
        growth_output = await _run_agent_streamed(idea_id, "growth_strategist", idea)
        financial_output = await _run_agent_streamed(idea_id, "financial_analyst", idea)
        legal_output = await _run_agent_streamed(idea_id, "legal_advisor", idea)
        operations_output = await _run_agent_streamed(idea_id, "operations_manager", idea)

        await bus.publish(idea_id, "phase", {"phase": "plan", "status": "completed"})

        return {
            "growth_strategy": growth_output,
            "financial_projection": financial_output,
            "legal_review": legal_output,
            "operations_plan": operations_output,
            "current_phase": "build",
            "messages": [f"[{_timestamp()}] Planning phase completed — growth, financial, legal, and operations plans generated."],
        }
    except Exception as e:
        logger.error("Plan node failed", error=str(e))
        await bus.publish(idea_id, "log", {"level": "error", "message": f"Planning phase error: {e}"})
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
    idea_id = _idea_id(state)

    await bus.publish(idea_id, "phase", {"phase": "build", "status": "started"})
    await bus.publish(idea_id, "log", {"level": "info", "message": "Synthesizing executive summary from all agent reports"})

    try:
        llm_service = get_llm_service()

        summary_prompt = (
            "You are a startup pitch expert. Based on the following research and analysis, "
            "create a compelling executive summary (2-3 pages) that an investor can read in 5 minutes.\n\n"
            f"## Startup Idea:\n{_format_idea(state['idea'])}\n\n"
            f"## Market Research:\n{state.get('market_research', 'N/A')[:2000]}\n\n"
            f"## Tech Architecture:\n{state.get('tech_architecture', 'N/A')[:2000]}\n\n"
            f"## Product Spec:\n{state.get('product_spec', 'N/A')[:2000]}\n\n"
            f"## Growth Strategy:\n{state.get('growth_strategy', 'N/A')[:2000]}\n\n"
            f"## Financial Projections:\n{state.get('financial_projection', 'N/A')[:2000]}\n\n"
            f"## Legal Review:\n{state.get('legal_review', 'N/A')[:1000]}\n\n"
            f"## Operations Plan:\n{state.get('operations_plan', 'N/A')[:1000]}\n\n"
            "Create an executive summary with these sections:\n"
            "1. The Problem & Opportunity\n"
            "2. Our Solution & Product Spec\n"
            "3. Market Opportunity (TAM/SAM/SOM)\n"
            "4. Business Model & Unit Economics\n"
            "5. Competitive Advantage\n"
            "6. Go-to-Market Strategy\n"
            "7. Financial Highlights & Operations Plan\n"
            "8. The Ask (funding amount and use of funds)\n"
        )

        executive_summary = await llm_service.generate(summary_prompt)
        await bus.publish(idea_id, "log", {"level": "success", "message": "Executive summary generated"})

        pitch_prompt = (
            "Based on all the research above, create a 12-slide pitch deck outline "
            "with specific content for each slide. Format as:\n"
            "SLIDE 1: [Title] - [Content]\n"
            "SLIDE 2: [Title] - [Content]\n"
            "... etc.\n\n"
            f"Context:\n{executive_summary[:3000]}\n"
        )

        pitch_deck = await llm_service.generate(pitch_prompt)
        await bus.publish(idea_id, "log", {"level": "success", "message": "Pitch deck content generated"})
        await bus.publish(idea_id, "phase", {"phase": "build", "status": "completed"})

        reports = [
            {"type": "market_research", "title": "Market Research Report", "status": "completed"},
            {"type": "tech_architecture", "title": "Technical Architecture", "status": "completed"},
            {"type": "product_spec", "title": "Product Specification", "status": "completed"},
            {"type": "growth_strategy", "title": "Growth Strategy", "status": "completed"},
            {"type": "financial_projection", "title": "Financial Projections", "status": "completed"},
            {"type": "operations_plan", "title": "Operations Plan", "status": "completed"},
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
        await bus.publish(idea_id, "log", {"level": "error", "message": f"Build phase error: {e}"})
        return {
            "errors": [f"Build failed: {str(e)}"],
            "current_phase": "simulate",
            "messages": [f"[{_timestamp()}] Build phase encountered errors: {str(e)}"],
        }


async def simulate_node(state: IncubatorState) -> dict:
    """
    SIMULATE NODE — Runs investor pitch simulation using AutoGen.
    Founder agent pitches to investor agents; every transcript turn is
    streamed to the dashboard as a `sim` event.
    """
    logger.info("Simulate node started")
    idea_id = _idea_id(state)

    await bus.publish(idea_id, "phase", {"phase": "simulate", "status": "started"})
    await bus.publish(idea_id, "log", {"level": "info", "message": "Investor pitch simulation — founder enters the room"})

    try:
        from app.simulation.pitch_engine import PitchEngine

        engine = PitchEngine()

        async def stream_turn(turn: dict) -> None:
            """Push each pitch turn to the dashboard the moment it happens."""
            await bus.publish(idea_id, "sim", {
                "speaker": turn.get("speaker", "Unknown"),
                "role": turn.get("role", ""),
                "content": turn.get("content", ""),
            })

        result = await engine.run_pitch(
            idea=state["idea"],
            executive_summary=state.get("executive_summary", ""),
            financial_projection=state.get("financial_projection", ""),
            on_turn=stream_turn,
        )

        outcome = result.get("outcome", "undetermined")
        await bus.publish(idea_id, "log", {
            "level": "success" if outcome == "funded" else "warn",
            "message": f"Simulation verdict: {outcome.upper()}",
        })
        await bus.publish(idea_id, "phase", {"phase": "simulate", "status": "completed"})

        return {
            "simulation_transcript": result.get("transcript", []),
            "simulation_outcome": outcome,
            "investor_feedback": result.get("feedback", {}),
            "funding_offered": result.get("funding_offered"),
            "valuation": result.get("valuation"),
            "current_phase": "completed",
            "status": "completed",
            "messages": [f"[{_timestamp()}] Simulation completed — outcome: {outcome}"],
        }
    except Exception as e:
        logger.error("Simulate node failed", error=str(e))
        await bus.publish(idea_id, "log", {"level": "error", "message": f"Simulation error: {e}"})
        return {
            "current_phase": "completed",
            "status": "completed",
            "errors": [f"Simulation failed: {str(e)}"],
            "messages": [f"[{_timestamp()}] Simulation skipped due to error. Incubation otherwise complete."],
        }


async def error_handler_node(state: IncubatorState) -> dict:
    """Handle workflow errors gracefully."""
    logger.warning("Error handler triggered", errors=state.get("errors", []))
    idea_id = _idea_id(state)
    await bus.publish(idea_id, "error", {
        "message": "; ".join(state.get("errors", [])[-3:]) or "Workflow encountered unrecoverable errors.",
    })
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
