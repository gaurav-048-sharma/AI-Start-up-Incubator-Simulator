"""
LangGraph Graph Assembly — Wires the full incubation state machine.
"""

import structlog
try:
    from langgraph.graph import StateGraph, END
except ImportError:
    END = "END"

    class _CompiledMockGraph:
        """A compiled mock graph that actually runs the nodes sequentially."""

        def __init__(self, nodes, entry_point, edges, conditional_edges):
            self._nodes = nodes
            self._entry = entry_point
            self._edges = edges  # {from_node: to_node}
            self._cond_edges = conditional_edges  # {from_node: (func, mapping)}

        async def astream(self, state, stream_mode="updates"):
            """Execute nodes sequentially following edges, yielding {node: update} dicts."""
            current = self._entry
            print(f"----- DEBUG ASTREAM START ----- current: {current}")
            while current and current != END:
                print(f"----- DEBUG ASTREAM LOOP ----- current: {current}")
                if current not in self._nodes:
                    print(f"----- DEBUG ASTREAM BREAK NOT IN NODES ----- current: {current}")
                    break
                node_fn = self._nodes[current]
                update = await node_fn(state)
                if isinstance(update, dict):
                    state.update(update)
                yield {current: update or {}}

                # Resolve next node
                if current in self._cond_edges:
                    route_fn, mapping = self._cond_edges[current]
                    decision = route_fn(state)
                    current = mapping.get(decision, None)
                elif current in self._edges:
                    current = self._edges[current]
                else:
                    break

    class StateGraph:
        """Fallback StateGraph that works without langgraph installed."""

        def __init__(self, *args, **kwargs):
            self._nodes = {}
            self._entry = None
            self._edges = {}
            self._cond_edges = {}

        def add_node(self, name, fn):
            self._nodes[name] = fn

        def set_entry_point(self, name):
            self._entry = name

        def add_edge(self, from_node, to_node):
            self._edges[from_node] = to_node

        def add_conditional_edges(self, from_node, route_fn, mapping):
            self._cond_edges[from_node] = (route_fn, mapping)

        def compile(self, *args, **kwargs):
            return _CompiledMockGraph(
                self._nodes, self._entry, self._edges, self._cond_edges
            )

from app.workflows.state import IncubatorState, DEFAULT_STATE
from uuid import uuid4
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

    from app.models.database import get_db_service
    db = get_db_service()

    progress_map = {
        "research": {"progress": 25, "status": "researching"},
        "validate": {"progress": 40, "status": "validating"},
        "plan": {"progress": 60, "status": "planning"},
        "build": {"progress": 80, "status": "planning"},
        "simulate": {"progress": 95, "status": "simulating"},
        "error_handler": {"progress": 100, "status": "failed"},
    }

    final_state = initial_state
    
    logger.info("Before astream loop", current_phase=initial_state.get("current_phase"), nodes=list(compiled_graph._nodes.keys()), entry=compiled_graph._entry)
    print("----- DEBUG BEFORE ASTREAM -----")
    print("compiled_graph nodes:", getattr(compiled_graph, "_nodes", "NO _NODES ATTR"))
    print("compiled_graph entry:", getattr(compiled_graph, "_entry", "NO _ENTRY ATTR"))
    print("--------------------------------")
    try:
        # Use stream_mode="updates" to get state updates after each node
        async for output in compiled_graph.astream(initial_state, stream_mode="updates"):
            logger.info("Yielded output", output_keys=list(output.keys()))
            for node_name, state_update in output.items():
                final_state.update(state_update)
                
                if node_name in progress_map:
                    update_info = progress_map[node_name]
                    await db.update_idea(idea["id"], update_info)
                
                # Log activities for the dashboard
                if node_name == "research":
                    await db.log_agent_activity({"id": str(uuid4()), "idea_id": idea["id"], "agent_name": "Market Analyst", "agent_role": "market_analyst", "action": "Conducted market research", "status": "completed"})
                    await db.log_agent_activity({"id": str(uuid4()), "idea_id": idea["id"], "agent_name": "Tech Architect", "agent_role": "tech_architect", "action": "Designed technical architecture", "status": "completed"})
                elif node_name == "validate":
                    await db.log_agent_activity({"id": str(uuid4()), "idea_id": idea["id"], "agent_name": "Quality Assurance", "agent_role": "qa", "action": "Validated research outputs", "status": "completed"})
                elif node_name == "plan":
                    await db.log_agent_activity({"id": str(uuid4()), "idea_id": idea["id"], "agent_name": "Growth Strategist", "agent_role": "strategist", "action": "Created go-to-market strategy", "status": "completed"})
                    await db.log_agent_activity({"id": str(uuid4()), "idea_id": idea["id"], "agent_name": "Financial Analyst", "agent_role": "finance", "action": "Generated financial projections", "status": "completed"})
                    await db.log_agent_activity({"id": str(uuid4()), "idea_id": idea["id"], "agent_name": "Legal Advisor", "agent_role": "legal", "action": "Conducted legal & IP review", "status": "completed"})
                elif node_name == "build":
                    await db.log_agent_activity({"id": str(uuid4()), "idea_id": idea["id"], "agent_name": "Tech Architect", "agent_role": "tech_architect", "action": "Drafted executive summary & pitch deck", "status": "completed"})
                elif node_name == "simulate":
                    await db.log_agent_activity({"id": str(uuid4()), "idea_id": idea["id"], "agent_name": "Investor Agents", "agent_role": "investor", "action": "Simulated investor pitch", "status": "completed"})

                # Create report records if generated
                if "reports" in state_update:
                    for rep in state_update["reports"]:
                        content = state_update.get(rep["type"]) or final_state.get(rep["type"], "Report content not generated yet.")
                        await db.create_report({
                            "id": str(uuid4()),
                            "idea_id": idea["id"],
                            "title": rep["title"],
                            "report_type": rep["type"],
                            "content": content,
                            "status": "completed"
                        })
    except Exception as e:
        logger.error("Error during astream", error=str(e), exc_info=True)
        final_state["status"] = "failed"

    logger.info(
        "Incubation workflow completed",
        status=final_state.get("status"),
        quality=final_state.get("overall_quality"),
        iterations=final_state.get("iteration"),
    )

    # Ensure it always reaches 100% at the end
    final_status = "failed" if final_state.get("status") == "failed" else "completed"
    await db.update_idea(idea["id"], {"progress": 100, "status": final_status})

    return dict(final_state)
