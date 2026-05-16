"""
Pydantic schemas for API request/response models.
These define the contracts between the frontend and backend.
"""

from datetime import datetime
from typing import Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID


# ── Enums ────────────────────────────────────────────────────────

class IdeaStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    RESEARCHING = "researching"
    VALIDATING = "validating"
    PLANNING = "planning"
    SIMULATING = "simulating"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRole(str, Enum):
    MARKET_ANALYST = "market_analyst"
    TECH_ARCHITECT = "tech_architect"
    GROWTH_STRATEGIST = "growth_strategist"
    FINANCIAL_ANALYST = "financial_analyst"
    LEGAL_ADVISOR = "legal_advisor"


class AgentStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


class ReportType(str, Enum):
    MARKET_ANALYSIS = "market_analysis"
    TECH_ARCHITECTURE = "tech_architecture"
    GROWTH_STRATEGY = "growth_strategy"
    FINANCIAL_PROJECTION = "financial_projection"
    LEGAL_REVIEW = "legal_review"
    PITCH_DECK = "pitch_deck"
    EXECUTIVE_SUMMARY = "executive_summary"
    FULL_REPORT = "full_report"


# ── Request Models ───────────────────────────────────────────────

class IdeaCreate(BaseModel):
    """Request body for creating a new startup idea."""
    title: str = Field(..., min_length=3, max_length=200, description="Startup idea title")
    description: str = Field(..., min_length=20, max_length=5000, description="Detailed description")
    industry: Optional[str] = Field(None, max_length=100, description="Target industry")
    target_market: Optional[str] = Field(None, max_length=500, description="Target market description")
    problem_statement: Optional[str] = Field(None, max_length=2000, description="Problem being solved")
    proposed_solution: Optional[str] = Field(None, max_length=2000, description="Proposed solution")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class IdeaUpdate(BaseModel):
    """Request body for updating a startup idea."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=20, max_length=5000)
    industry: Optional[str] = Field(None, max_length=100)
    target_market: Optional[str] = Field(None, max_length=500)
    problem_statement: Optional[str] = Field(None, max_length=2000)
    proposed_solution: Optional[str] = Field(None, max_length=2000)
    metadata: Optional[dict[str, Any]] = None


class SimulationCreate(BaseModel):
    """Request body for starting an investor pitch simulation."""
    simulation_type: str = Field(default="pitch", description="Type of simulation")
    investor_profiles: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Custom investor profiles. If None, defaults are used.",
    )
    founder_context: Optional[str] = Field(
        None,
        description="Additional context the founder wants to share during the pitch.",
    )


class SimulationRespond(BaseModel):
    """Request body for the founder's response during a simulation."""
    message: str = Field(..., min_length=1, max_length=5000, description="Founder's response")


# ── Response Models ──────────────────────────────────────────────

class ProfileResponse(BaseModel):
    """User profile response."""
    id: UUID
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    company_name: Optional[str] = None
    role: str = "founder"
    credits: int = 10
    created_at: datetime
    updated_at: datetime


class IdeaResponse(BaseModel):
    """Startup idea response."""
    id: UUID
    user_id: UUID
    title: str
    description: str
    industry: Optional[str] = None
    target_market: Optional[str] = None
    problem_statement: Optional[str] = None
    proposed_solution: Optional[str] = None
    status: IdeaStatus = IdeaStatus.DRAFT
    current_phase: Optional[str] = None
    progress: int = 0
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class IdeaListResponse(BaseModel):
    """Paginated list of ideas."""
    ideas: list[IdeaResponse]
    total: int


class AgentActivityResponse(BaseModel):
    """Agent activity event response."""
    id: UUID
    idea_id: UUID
    agent_name: str
    agent_role: str
    action: str
    status: AgentStatus
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class WorkflowStateResponse(BaseModel):
    """Workflow state response."""
    id: UUID
    idea_id: UUID
    graph_state: dict[str, Any]
    current_node: str
    iteration: int = 0
    quality_score: Optional[float] = None
    decision_log: list[dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime


class WorkflowGraphResponse(BaseModel):
    """Workflow graph structure for visualization."""
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    current_node: Optional[str] = None


class ReportResponse(BaseModel):
    """Generated report response."""
    id: UUID
    idea_id: UUID
    report_type: ReportType
    title: str
    content: dict[str, Any]
    file_url: Optional[str] = None
    version: int = 1
    created_at: datetime


class SimulationResponse(BaseModel):
    """Investor simulation response."""
    id: UUID
    idea_id: UUID
    simulation_type: str = "pitch"
    investor_profiles: list[dict[str, Any]]
    transcript: list[dict[str, Any]] = []
    outcome: Optional[str] = None
    funding_offered: Optional[float] = None
    valuation: Optional[float] = None
    feedback: Optional[dict[str, Any]] = None
    score: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


# ── WebSocket Event Models ──────────────────────────────────────

class WSAgentEvent(BaseModel):
    """WebSocket event for agent activity updates."""
    event_type: str = "agent_update"
    idea_id: str
    agent_name: str
    agent_role: str
    action: str
    status: str
    output: Optional[str] = None
    progress: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSWorkflowEvent(BaseModel):
    """WebSocket event for workflow state changes."""
    event_type: str = "workflow_update"
    idea_id: str
    current_node: str
    previous_node: Optional[str] = None
    iteration: int = 0
    quality_score: Optional[float] = None
    decision: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSSimulationEvent(BaseModel):
    """WebSocket event for simulation dialogue."""
    event_type: str = "simulation_update"
    simulation_id: str
    speaker: str
    role: str  # 'founder' or 'investor'
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Utility Models ───────────────────────────────────────────────

class LaunchResponse(BaseModel):
    """Response when launching the incubation workflow."""
    idea_id: UUID
    status: str = "launched"
    message: str = "Incubation workflow started successfully."
    workflow_id: Optional[UUID] = None


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str
    detail: Optional[str] = None
    status_code: int = 400
