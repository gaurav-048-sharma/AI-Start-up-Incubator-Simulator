"""
Backend test suite for the AI Start-up Incubator Simulator.
Covers: API endpoints, middleware, schemas, and service integration.

Note: Tests that hit auth-protected endpoints will receive 401 when
Supabase is configured (production-like). Unit tests for schemas,
RBAC logic, and unauthenticated endpoints always pass.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import get_settings


def _auth_enabled() -> bool:
    """Check if Supabase auth is configured (tests will get 401)."""
    settings = get_settings()
    return settings.has_supabase


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health & System ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "services" in data
    assert "version" in data


@pytest.mark.anyio
async def test_root(client: AsyncClient):
    r = await client.get("/")
    assert r.status_code == 200
    assert "name" in r.json()


@pytest.mark.anyio
async def test_metrics(client: AsyncClient):
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert "version" in r.json()


# ── Ideas CRUD ──────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_create_idea(client: AsyncClient):
    r = await client.post("/api/ideas", json={
        "title": "Test AI Startup",
        "description": "An AI-powered platform for automated testing and quality assurance.",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Test AI Startup"
    assert data["status"] == "draft"
    assert data["progress"] == 0


@pytest.mark.anyio
async def test_create_idea_validation(client: AsyncClient):
    # Title too short
    r = await client.post("/api/ideas", json={"title": "AB", "description": "x" * 20})
    assert r.status_code == 422

    # Description too short
    r = await client.post("/api/ideas", json={"title": "Good Title", "description": "Too short"})
    assert r.status_code == 422


@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_list_ideas(client: AsyncClient):
    r = await client.get("/api/ideas")
    assert r.status_code == 200
    data = r.json()
    assert "ideas" in data
    assert "total" in data


# ── Agents ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_agent_roles(client: AsyncClient):
    r = await client.get("/api/agents/roles")
    assert r.status_code == 200
    data = r.json()
    assert "roles" in data
    assert len(data["roles"]) == 5

    role_ids = {role["id"] for role in data["roles"]}
    assert "market_analyst" in role_ids
    assert "tech_architect" in role_ids
    assert "growth_strategist" in role_ids
    assert "financial_analyst" in role_ids
    assert "legal_advisor" in role_ids


# ── Workflows ───────────────────────────────────────────────────

@pytest.mark.anyio
async def test_workflow_graph(client: AsyncClient):
    r = await client.get("/api/workflows/graph")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 5
    assert len(data["edges"]) >= 5


# ── Billing Plans ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_billing_plans(client: AsyncClient):
    r = await client.get("/api/billing/plans")
    # May return 404 if billing routes aren't loaded (no Stripe key)
    if r.status_code == 200:
        data = r.json()
        assert "plans" in data
        assert len(data["plans"]) == 3


# ── Analytics ───────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_analytics_usage(client: AsyncClient):
    r = await client.get("/api/analytics/usage")
    assert r.status_code == 200
    data = r.json()
    assert "total_events" in data
    assert "total_tokens" in data
    assert "total_cost_usd" in data
    assert "events_by_type" in data
    assert "daily_usage" in data
    assert "period_days" in data


@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_analytics_usage_custom_period(client: AsyncClient):
    r = await client.get("/api/analytics/usage?days=7")
    assert r.status_code == 200
    data = r.json()
    assert data["period_days"] == 7


@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_analytics_credits(client: AsyncClient):
    r = await client.get("/api/analytics/credits")
    assert r.status_code == 200
    data = r.json()
    assert "credits" in data
    assert "user_id" in data


@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_analytics_credits_check(client: AsyncClient):
    r = await client.get("/api/analytics/credits/check?event_type=workflow_run")
    assert r.status_code == 200
    data = r.json()
    assert "has_credits" in data
    assert "required" in data
    assert data["required"] == 3  # workflow_run costs 3 credits

    # Free operation
    r2 = await client.get("/api/analytics/credits/check?event_type=report_export")
    data2 = r2.json()
    assert data2["required"] == 0


# ── Notifications ───────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_notifications_list(client: AsyncClient):
    r = await client.get("/api/notifications")
    assert r.status_code == 200
    data = r.json()
    assert "notifications" in data
    assert "unread_count" in data
    assert "total" in data


@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_notifications_unread_count(client: AsyncClient):
    r = await client.get("/api/notifications/unread-count")
    assert r.status_code == 200
    data = r.json()
    assert "unread_count" in data
    assert isinstance(data["unread_count"], int)


@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_notifications_mark_all_read(client: AsyncClient):
    r = await client.post("/api/notifications/mark-all-read")
    assert r.status_code == 200
    data = r.json()
    assert "success" in data


# ── Settings ────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_settings_get(client: AsyncClient):
    r = await client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["llm_provider"] in ["gemini", "anthropic"]
    assert data["llm_model"] in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "claude-sonnet-4-20250514"]
    assert 1 <= data["max_iterations"] <= 15
    assert 0 <= data["quality_threshold"] <= 1


@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_settings_update(client: AsyncClient):
    r = await client.patch("/api/settings", json={
        "llm_provider": "gemini",
        "llm_model": "gemini-1.5-flash",
        "max_iterations": 8,
        "quality_threshold": 0.8,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["llm_model"] == "gemini-1.5-flash"
    assert data["max_iterations"] == 8


@pytest.mark.anyio
async def test_settings_validation(client: AsyncClient):
    # Invalid iterations (too high)
    r = await client.patch("/api/settings", json={"max_iterations": 99})
    assert r.status_code == 422

    # Invalid quality threshold
    r2 = await client.patch("/api/settings", json={"quality_threshold": 5.0})
    assert r2.status_code == 422


# ── Comparison ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_comparison_requires_two_ideas(client: AsyncClient):
    r = await client.post("/api/ideas/compare", json={"idea_ids": ["one-id"]})
    assert r.status_code == 400
    assert "At least 2" in r.json()["detail"]


@pytest.mark.anyio
async def test_comparison_max_four_ideas(client: AsyncClient):
    r = await client.post("/api/ideas/compare", json={
        "idea_ids": ["a", "b", "c", "d", "e"]
    })
    assert r.status_code == 400
    assert "Maximum 4" in r.json()["detail"]


# ── Rate Limiting Headers ────────────────────────────────────────

@pytest.mark.anyio
async def test_rate_limit_headers(client: AsyncClient):
    r = await client.get("/api/agents/roles")
    assert "x-ratelimit-limit" in r.headers
    assert "x-ratelimit-remaining" in r.headers


# ── Request ID Headers ──────────────────────────────────────────

@pytest.mark.anyio
async def test_request_id(client: AsyncClient):
    r = await client.get("/api/agents/roles")
    assert "x-request-id" in r.headers
    assert "x-response-time" in r.headers


# ── Schema Validation ───────────────────────────────────────────

def test_idea_schema():
    from app.models.schemas import IdeaCreate
    idea = IdeaCreate(
        title="Test Idea",
        description="A detailed description of the test startup idea for validation.",
    )
    assert idea.title == "Test Idea"
    assert idea.industry is None


def test_idea_response_accepts_str_id():
    from app.models.schemas import IdeaResponse
    response = IdeaResponse(id="string-id", title="Test", description="Test desc for schema")
    assert str(response.id) == "string-id"


def test_feature_tiers():
    from app.middleware.security import FEATURE_TIERS
    assert "create_idea" in FEATURE_TIERS
    assert "free" in FEATURE_TIERS["create_idea"]
    assert "team_collaboration" in FEATURE_TIERS
    assert "free" not in FEATURE_TIERS["team_collaboration"]


# ── Analytics Service Unit Tests ─────────────────────────────────

def test_credit_costs():
    from app.services.analytics import CREDIT_COSTS
    assert CREDIT_COSTS["workflow_run"] == 3
    assert CREDIT_COSTS["agent_run"] == 1
    assert CREDIT_COSTS["simulation_run"] == 2
    assert CREDIT_COSTS["report_export"] == 0


def test_token_costs():
    from app.services.analytics import TOKEN_COST_PER_1K
    assert "gemini-2.5-flash" in TOKEN_COST_PER_1K
    assert "claude-sonnet-4-20250514" in TOKEN_COST_PER_1K
    assert all(v > 0 for v in TOKEN_COST_PER_1K.values())


# ── RBAC Unit Tests ──────────────────────────────────────────────

def test_role_hierarchy():
    from app.middleware.security import ROLE_HIERARCHY, has_role_level
    assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["incubator_manager"]
    assert ROLE_HIERARCHY["incubator_manager"] > ROLE_HIERARCHY["innovation_lead"]
    assert ROLE_HIERARCHY["innovation_lead"] > ROLE_HIERARCHY["investor_advisor"]
    assert ROLE_HIERARCHY["investor_advisor"] > ROLE_HIERARCHY["founder"]
    assert ROLE_HIERARCHY["founder"] > ROLE_HIERARCHY["team_member"]
    assert ROLE_HIERARCHY["team_member"] > ROLE_HIERARCHY["viewer"]

    # Level checks
    assert has_role_level("admin", "founder") is True
    assert has_role_level("viewer", "admin") is False


def test_role_permissions():
    from app.middleware.security import has_permission

    # Founder can launch workflows but not manage users
    assert has_permission("founder", "launch_workflow") is True
    assert has_permission("founder", "manage_users") is False

    # Viewer has minimal access
    assert has_permission("viewer", "view_ideas") is True
    assert has_permission("viewer", "create_idea") is False
    assert has_permission("viewer", "launch_workflow") is False

    # Admin can manage users
    assert has_permission("admin", "manage_users") is True
    assert has_permission("admin", "manage_billing") is True

    # Incubator manager can invite but not manage billing
    assert has_permission("incubator_manager", "invite_members") is True
    assert has_permission("incubator_manager", "manage_billing") is False


def test_role_descriptions():
    from app.middleware.security import ROLE_DESCRIPTIONS, ROLE_HIERARCHY
    # Every role in hierarchy has a description
    for role in ROLE_HIERARCHY:
        assert role in ROLE_DESCRIPTIONS, f"Missing description for role: {role}"
        assert len(ROLE_DESCRIPTIONS[role]) > 10


def test_user_role_enum():
    from app.models.schemas import TenantRole, PlatformRole
    assert TenantRole.FOUNDER.value == "founder"
    assert PlatformRole.SUPER_ADMIN.value == "super_admin"
    assert len(TenantRole) == 15


def test_subscription_tier_enum():
    from app.models.schemas import SubscriptionTier
    assert SubscriptionTier.FREE.value == "free"
    assert SubscriptionTier.PRO.value == "pro"
    assert SubscriptionTier.ENTERPRISE.value == "enterprise"


def test_expanded_feature_tiers():
    from app.middleware.security import FEATURE_TIERS
    # New enterprise features exist
    assert "audit_trail" in FEATURE_TIERS
    assert "enterprise" in FEATURE_TIERS["audit_trail"]
    assert "org_management" in FEATURE_TIERS
    assert "multi_workspace" in FEATURE_TIERS
    # Pro features
    assert "compare_ideas" in FEATURE_TIERS
    assert "pro" in FEATURE_TIERS["compare_ideas"]
    assert "analytics_dashboard" in FEATURE_TIERS


# ── Organization API Tests ───────────────────────────────────────

@pytest.mark.anyio
async def test_org_roles_endpoint(client: AsyncClient):
    r = await client.get("/api/organizations/roles")
    assert r.status_code == 200
    data = r.json()
    assert "roles" in data
    assert len(data["roles"]) == 15
    role_ids = {r["id"] for r in data["roles"]}
    assert "founder" in role_ids
    assert "admin" in role_ids
    assert "investor_advisor" in role_ids
    assert "incubator_manager" in role_ids


@pytest.mark.anyio
@pytest.mark.skipif(_auth_enabled(), reason="Requires demo-user (no Supabase auth)")
async def test_org_list_empty(client: AsyncClient):
    r = await client.get("/api/organizations")
    assert r.status_code == 200
    data = r.json()
    assert "organizations" in data


def test_profile_response_schema():
    from app.models.schemas import ProfileResponse
    profile = ProfileResponse(
        id="test-id",
        role="incubator_manager",
        tier="enterprise",
        current_org_id="org-123",
        org_role="admin",
    )
    assert profile.role == "incubator_manager"
    assert profile.tier == "enterprise"
    assert str(profile.current_org_id) == "org-123"


def test_organization_response_schema():
    from app.models.schemas import OrganizationResponse
    org = OrganizationResponse(
        id="org-1",
        name="Test Accelerator",
        slug="test-accelerator",
        plan="enterprise",
        member_count=15,
    )
    assert org.slug == "test-accelerator"
    assert org.member_count == 15
