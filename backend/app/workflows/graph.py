"""
LangGraph Graph Assembly — Wires the full incubation state machine.
"""

import structlog
from langgraph.graph import StateGraph, END

from app.workflows.state import IncubatorState, DEFAULT_STATE
from app.workflows.nodes import (
    research_node,
    validate_node,
    plan_node,
    build_node,
    simulate_node,
    error_handler_node,
)
from app.workflows.edges import (
    route_after_validation,
    route_after_planning,
    route_after_build,
)

logger = structlog.get_logger()


def build_incubator_graph() -> StateGraph:
    """
    Build the complete incubation workflow graph.

    Flow:
    research → validate → (loop back or proceed) → plan → build → simulate → END
                                                     ↓
                                               error_handler → END
    """
    graph = StateGraph(IncubatorState)

    # Add nodes
    graph.add_node("research", research_node)
    graph.add_node("validate", validate_node)
    graph.add_node("plan", plan_node)
    graph.add_node("build", build_node)
    graph.add_node("simulate", simulate_node)
    graph.add_node("error_handler", error_handler_node)

    # Set entry point
    graph.set_entry_point("research")

    # Add edges
    graph.add_edge("research", "validate")

    # Conditional: validate → research (loop) or plan (proceed)
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {"research": "research", "plan": "plan"},
    )

    # Conditional: plan → build or error_handler
    graph.add_conditional_edges(
        "plan",
        route_after_planning,
        {"build": "build", "error_handler": "error_handler"},
    )

    # Conditional: build → simulate or end
    graph.add_conditional_edges(
        "build",
        route_after_build,
        {"simulate": "simulate", "end": END},
    )

    # Terminal edges
    graph.add_edge("simulate", END)
    graph.add_edge("error_handler", END)

    logger.info("Incubator graph built successfully")
    return graph


def compile_incubator_graph():
    """Compile the graph into a runnable."""
    graph = build_incubator_graph()
    return graph.compile()


def get_graph_structure() -> dict:
    """Return the graph structure for frontend visualization."""
    return {
        "nodes": [
            {"id": "research", "label": "Research", "type": "agent", "description": "Market Analysis & Tech Architecture"},
            {"id": "validate", "label": "Quality Gate", "type": "decision", "description": "Evaluate research quality"},
            {"id": "plan", "label": "Plan", "type": "agent", "description": "Growth Strategy, Financials & Legal"},
            {"id": "build", "label": "Build", "type": "process", "description": "Executive Summary & Pitch Deck"},
            {"id": "simulate", "label": "Simulate", "type": "agent", "description": "Investor Pitch Simulation"},
            {"id": "error_handler", "label": "Error Handler", "type": "error", "description": "Handle workflow failures"},
            {"id": "end", "label": "Complete", "type": "terminal", "description": "Workflow finished"},
        ],
        "edges": [
            {"from": "research", "to": "validate", "label": ""},
            {"from": "validate", "to": "plan", "label": "Quality ≥ 0.7", "type": "conditional"},
            {"from": "validate", "to": "research", "label": "Quality < 0.7", "type": "conditional"},
            {"from": "plan", "to": "build", "label": "No errors", "type": "conditional"},
            {"from": "plan", "to": "error_handler", "label": "Critical errors", "type": "conditional"},
            {"from": "build", "to": "simulate", "label": "Summary generated", "type": "conditional"},
            {"from": "build", "to": "end", "label": "Build failed", "type": "conditional"},
            {"from": "simulate", "to": "end", "label": ""},
            {"from": "error_handler", "to": "end", "label": ""},
        ],
    }


async def run_incubation_workflow(idea: dict, user_id: str) -> dict:
    """
    Execute the full incubation workflow for a startup idea.

    Args:
        idea: The startup idea dict.
        user_id: The user ID who submitted the idea.

    Returns:
        The final workflow state with all agent outputs.
    """
    compiled_graph = compile_incubator_graph()

    initial_state = {
        **DEFAULT_STATE,
        "idea_id": idea.get("id", ""),
        "idea": idea,
        "user_id": user_id,
    }

    logger.info("Starting incubation workflow", idea_title=idea.get("title"))

    final_state = await compiled_graph.ainvoke(initial_state)

    logger.info(
        "Incubation workflow completed",
        status=final_state.get("status"),
        quality=final_state.get("overall_quality"),
        iterations=final_state.get("iteration"),
    )

    return dict(final_state)
