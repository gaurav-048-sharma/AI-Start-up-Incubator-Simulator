"""
LangGraph State Schema — Defines the typed state for the incubation workflow.
This state flows through all nodes and edges in the workflow graph.
"""

from typing import Optional, Annotated
from typing_extensions import TypedDict
import operator


def merge_dicts(a: dict, b: dict) -> dict:
    """Merge two dicts, with b overwriting a."""
    merged = {**a, **b}
    return merged


class IncubatorState(TypedDict, total=False):
    """
    The complete state of an incubation workflow.
    Flows through all LangGraph nodes — each node reads and writes to this state.
    """

    # ── Input ────────────────────────────────────────────────────
    idea_id: str
    idea: dict  # The startup idea (title, description, etc.)
    user_id: str

    # ── Workflow Control ─────────────────────────────────────────
    current_phase: str  # Current phase: research, validate, plan, build, simulate
    iteration: Annotated[int, operator.add]  # Iteration counter (auto-incremented)
    max_iterations: int  # Maximum iterations before forced completion
    status: str  # overall status: running, completed, failed
    errors: Annotated[list[str], operator.add]  # Accumulated errors

    # ── Agent Outputs ────────────────────────────────────────────
    market_research: str  # Market Analyst output
    tech_architecture: str  # Tech Architect output
    product_spec: str  # Product Manager output
    growth_strategy: str  # Growth Strategist output
    financial_projection: str  # Financial Analyst output
    operations_plan: str  # Operations Manager output
    legal_review: str  # Legal Advisor output

    # ── Quality Scores ───────────────────────────────────────────
    quality_scores: Annotated[dict, merge_dicts]  # Per-section quality scores
    overall_quality: float  # Weighted overall quality score (0-1)
    quality_feedback: Annotated[list[str], operator.add]  # Quality gate feedback

    # ── Simulation ───────────────────────────────────────────────
    simulation_transcript: list[dict]  # Pitch simulation messages
    simulation_outcome: Optional[str]  # Outcome: funded, rejected, conditional
    investor_feedback: Optional[dict]  # Structured investor feedback
    funding_offered: Optional[float]
    valuation: Optional[float]

    # ── Reports ──────────────────────────────────────────────────
    reports: Annotated[list[dict], operator.add]  # Generated report metadata
    executive_summary: str  # Final executive summary
    pitch_deck_content: str  # Generated pitch deck content

    # ── Decision Log ─────────────────────────────────────────────
    decisions: Annotated[list[dict], operator.add]  # All routing decisions made
    messages: Annotated[list[str], operator.add]  # Human-readable status messages


# Default state for new workflows
DEFAULT_STATE: dict = {
    "current_phase": "research",
    "iteration": 0,
    "max_iterations": 5,
    "status": "running",
    "errors": [],
    "market_research": "",
    "tech_architecture": "",
    "product_spec": "",
    "growth_strategy": "",
    "financial_projection": "",
    "operations_plan": "",
    "legal_review": "",
    "quality_scores": {},
    "overall_quality": 0.0,
    "quality_feedback": [],
    "simulation_transcript": [],
    "simulation_outcome": None,
    "investor_feedback": None,
    "funding_offered": None,
    "valuation": None,
    "reports": [],
    "executive_summary": "",
    "pitch_deck_content": "",
    "decisions": [],
    "messages": [],
}
