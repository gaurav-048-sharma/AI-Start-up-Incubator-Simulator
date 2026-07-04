"""
Pydantic schemas for API request/response models.
These define the contracts between the frontend and backend.
"""

from datetime import datetime, timezone
from typing import Optional, Any, Union
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
    PROCESSING = "processing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PlatformRole(str, Enum):
    """Global system-level roles."""
    USER = "user"
    SUPPORT = "support"
    BILLING_ADMIN = "billing_admin"
    SUPER_ADMIN = "super_admin"


class TenantRole(str, Enum):
    """Organization-scoped roles (tenant context)."""
    VIEWER = "viewer"
    TEAM_MEMBER = "team_member"
    FOUNDER = "founder"
    INVESTOR_ADVISOR = "investor_advisor"
    INNOVATION_LEAD = "innovation_lead"
    INCUBATOR_MANAGER = "incubator_manager"
    ADMIN = "admin"
    WORKSPACE_OWNER = "workspace_owner"



class SubscriptionTier(str, Enum):
    """Billing subscription tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


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
    MARKET_RESEARCH = "market_research"
    TECH_ARCHITECTURE = "tech_architecture"
    GROWTH_STRATEGY = "growth_strategy"
    FINANCIAL_PROJECTION = "financial_projection"
    LEGAL_REVIEW = "legal_review"
    PITCH_DECK = "pitch_deck"
    PITCH_DECK_CONTENT = "pitch_deck_content"
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
    department_id: Optional[str] = Field(None, description="Department to scope this idea to")
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
    id: Union[str, UUID]
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    company_name: Optional[str] = None
    current_org_id: Optional[Union[str, UUID]] = None
    role: str = "founder"
    platform_role: str = "user"
    tier: str = "free"
    credits: int = 10
    total_ideas_created: int = 0
    total_workflows_run: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OrganizationResponse(BaseModel):
    """Organization response."""
    id: Union[str, UUID]
    name: str
    slug: str
    logo_url: Optional[str] = None
    plan: str = "free"
    owner_id: Optional[Union[str, UUID]] = None
    max_members: int = 5
    max_ideas: int = 20
    sso_provider: Optional[str] = None
    sso_entity_id: Optional[str] = None
    sso_acs_url: Optional[str] = None
    sso_enforced: bool = False
    member_count: Optional[int] = None
    my_role: Optional[str] = None
    created_at: Optional[datetime] = None


class OrganizationMemberResponse(BaseModel):
    """Organization member response."""
    id: Union[str, UUID]
    user_id: Union[str, UUID]
    role: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    joined_at: Optional[datetime] = None


class IdeaResponse(BaseModel):
    """Startup idea response."""
    id: Union[str, UUID]
    user_id: Union[str, UUID] = "demo-user"
    organization_id: Optional[Union[str, UUID]] = None
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IdeaListResponse(BaseModel):
    """Paginated list of ideas."""
    ideas: list[IdeaResponse]
    total: int


class AgentActivityResponse(BaseModel):
    """Agent activity event response."""
    id: Union[str, UUID]
    idea_id: Union[str, UUID]
    agent_name: str
    agent_role: str
    action: str
    status: AgentStatus
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowStateResponse(BaseModel):
    """Workflow state response."""
    id: Union[str, UUID]
    idea_id: Union[str, UUID]
    graph_state: dict[str, Any]
    current_node: str
    iteration: int = 0
    quality_score: Optional[float] = None
    decision_log: list[dict[str, Any]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkflowGraphResponse(BaseModel):
    """Workflow graph structure for visualization."""
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    current_node: Optional[str] = None


class ReportResponse(BaseModel):
    """Generated report response."""
    id: Union[str, UUID]
    idea_id: Union[str, UUID]
    report_type: ReportType
    title: str
    content: Any  # Can be dict or string (markdown)
    file_url: Optional[str] = None
    version: int = 1
    created_at: Optional[datetime] = None


class SimulationResponse(BaseModel):
    """Investor simulation response."""
    id: Union[str, UUID]
    idea_id: Union[str, UUID]
    organization_id: Optional[Union[str, UUID]] = None
    simulation_type: str = "pitch"
    investor_profiles: Any = []
    transcript: list[dict[str, Any]] = []
    outcome: Optional[str] = None
    funding_offered: Optional[float] = None
    valuation: Optional[float] = None
    feedback: Optional[dict[str, Any]] = None
    score: Optional[float] = None
    started_at: Optional[datetime] = None
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
    idea_id: Union[str, UUID]
    status: str = "launched"
    message: str = "Incubation workflow started successfully."
    workflow_id: Optional[Union[str, UUID]] = None


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str
    detail: Optional[str] = None
    status_code: int = 400
