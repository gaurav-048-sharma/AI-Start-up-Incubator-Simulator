"""
LangGraph Conditional Edges — Defines routing logic between workflow nodes.
Implements quality gates, iteration limits, and phase transitions.
"""

import structlog
from app.workflows.state import IncubatorState
from app.config import get_settings

logger = structlog.get_logger()


def route_after_validation(state: IncubatorState) -> str:
    """
    Quality gate router after validation.
    Loops back to research if quality is too low and iterations remain.
    """
    settings = get_settings()
    quality = state.get("overall_quality", 0.0)
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", settings.workflow_max_iterations)
    threshold = settings.quality_threshold

    if quality >= threshold:
        logger.info("Quality gate PASSED", quality=quality)
        return "plan"

    if iteration < max_iter:
        logger.info("Quality gate FAILED — looping", quality=quality, iteration=iteration)
        return "research"

    logger.warning("Max iterations reached — proceeding anyway")
    return "plan"


def route_after_planning(state: IncubatorState) -> str:
    """Route to error handler if critical errors, else to build."""
    errors = state.get("errors", [])
    critical = [e for e in errors if "critical" in e.lower()]
    return "error_handler" if critical else "build"


def route_after_build(state: IncubatorState) -> str:
    """Route to simulate if build succeeded, else end."""
    summary = state.get("executive_summary", "")
    return "simulate" if summary and len(summary) > 100 else "end"


def should_continue(state: IncubatorState) -> str:
    """General continuation check."""
    if state.get("status") in ("completed", "failed"):
        return "end"
    if len(state.get("errors", [])) > 10:
        return "end"
    return "continue"
