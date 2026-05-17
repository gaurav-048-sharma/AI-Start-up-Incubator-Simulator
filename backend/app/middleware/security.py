"""
Security middleware stack for the AI Incubator backend.
Provides: rate limiting, request correlation IDs, JWT auth, enterprise RBAC,
multi-tenant org context, audit logging, and feature gating.
"""

import uuid
import time
import structlog
from collections import defaultdict
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional
from datetime import datetime, timezone

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# ROLE HIERARCHY — defines who can do what
# Higher numbers = more permissions. Each role inherits lower roles.
# ═══════════════════════════════════════════════════════════════════

ROLE_HIERARCHY = {
    "viewer":            10,
    "team_member":       20,
    "founder":           30,
    "investor_advisor":  40,
    "innovation_lead":   50,
    "incubator_manager": 60,
    "admin":             70,
    "super_admin":       80,
}

ROLE_DESCRIPTIONS = {
    "viewer":            "Read-only access to shared ideas and reports",
    "team_member":       "Collaborate on ideas, view reports, contribute to workflows",
    "founder":           "Full access to own ideas, simulations, reports, and subscriptions",
    "investor_advisor":  "Review startup simulations, provide feedback, access pitch data",
    "innovation_lead":   "Manage internal projects, organizational teams, white-label settings",
    "incubator_manager": "Oversee cohorts, all startups, team performance, analytics dashboards",
    "admin":             "Manage users, billing, feature flags, moderation, platform support",
    "super_admin":       "Full platform operations, infrastructure, analytics, monetization",
}

# Which roles can perform which actions
ROLE_PERMISSIONS = {
    "viewer": [
        "view_ideas", "view_reports", "view_workflows",
    ],
    "team_member": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "view_agents",
    ],
    "founder": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "view_agents",
        "launch_workflow", "run_simulation", "view_analytics",
        "manage_own_settings", "export_reports",
    ],
    "investor_advisor": [
        "view_ideas", "view_reports", "view_workflows",
        "view_simulations", "provide_feedback", "view_analytics",
    ],
    "innovation_lead": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "view_agents",
        "launch_workflow", "run_simulation", "view_analytics",
        "manage_own_settings", "export_reports",
        "manage_team_ideas", "view_org_analytics",
    ],
    "incubator_manager": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "edit_all_ideas", "view_agents",
        "launch_workflow", "run_simulation", "view_analytics",
        "manage_own_settings", "export_reports",
        "manage_team_ideas", "view_org_analytics",
        "manage_cohorts", "invite_members", "view_audit_log",
    ],
    "admin": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "edit_all_ideas", "delete_ideas", "view_agents",
        "launch_workflow", "run_simulation", "view_analytics",
        "manage_own_settings", "export_reports",
        "manage_team_ideas", "view_org_analytics",
        "manage_cohorts", "invite_members", "remove_members", "view_audit_log",
        "manage_billing", "manage_feature_flags", "manage_users", "manage_org",
    ],
    "super_admin": ["*"],  # All permissions
}


def has_permission(user_role: str, required_permission: str) -> bool:
    """Check if a role has a specific permission."""
    perms = ROLE_PERMISSIONS.get(user_role, [])
    return "*" in perms or required_permission in perms


def has_role_level(user_role: str, minimum_role: str) -> bool:
    """Check if the user's role level meets or exceeds the minimum."""
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    min_level = ROLE_HIERARCHY.get(minimum_role, 999)
    return user_level >= min_level


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory sliding window rate limiter.
    For production, replace with Redis-backed SlowAPI.
    """

    def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst = burst_limit
        self._windows: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_window(self, key: str, now: float):
        cutoff = now - 60.0
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and WebSockets
        if request.url.path in ("/health", "/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)
        if request.url.path.startswith("/ws/"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        self._clean_window(client_ip, now)

        if len(self._windows[client_ip]) >= self.rpm:
            logger.warning("Rate limit exceeded", client_ip=client_ip, path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "detail": f"Max {self.rpm} requests per minute"},
                headers={"Retry-After": "60"},
            )

        self._windows[client_ip].append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(self.rpm - len(self._windows[client_ip]))
        return response


# ── Request ID Middleware ────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds a unique X-Request-ID header to every request for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ── Request Timing ───────────────────────────────────────────────

class TimingMiddleware(BaseHTTPMiddleware):
    """Logs request duration for performance monitoring."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        if request.url.path not in ("/health", "/"):
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        return response


# ═══════════════════════════════════════════════════════════════════
# AUTH DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """
    Validates the Supabase JWT and returns the user payload with role and org info.
    Falls back to demo-user when auth is not configured.
    """
    from app.config import get_settings
    settings = get_settings()

    # In development without Supabase, allow demo access
    if not settings.has_supabase:
        return {
            "id": "demo-user",
            "email": "demo@incubator.ai",
            "role": "founder",
            "tier": "free",
            "org_id": None,
            "org_role": None,
            "full_name": "Demo Founder",
        }

    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        from supabase import create_client
        supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
        user_response = supabase.auth.get_user(credentials.credentials)

        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user = user_response.user
        user_id = str(user.id)
        user_role = user.user_metadata.get("role", "founder")
        user_tier = user.user_metadata.get("tier", "free")

        # Fetch organization membership if exists
        org_id = None
        org_role = None
        try:
            profile = supabase.table("profiles").select("current_org_id").eq("id", user_id).single().execute()
            if profile.data and profile.data.get("current_org_id"):
                org_id = profile.data["current_org_id"]

                membership = (
                    supabase.table("organization_members")
                    .select("role")
                    .eq("organization_id", org_id)
                    .eq("user_id", user_id)
                    .single()
                    .execute()
                )
                if membership.data:
                    org_role = membership.data["role"]
                    # Org role overrides user role if it's higher
                    if has_role_level(org_role, user_role):
                        user_role = org_role
        except Exception:
            pass  # No org context is fine

        return {
            "id": user_id,
            "email": user.email,
            "role": user_role,
            "tier": user_tier,
            "org_id": org_id,
            "org_role": org_role,
            "full_name": user.user_metadata.get("full_name", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Auth validation failed", error=str(e))
        raise HTTPException(status_code=401, detail="Authentication failed")


# ═══════════════════════════════════════════════════════════════════
# RBAC DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════

def require_role(*allowed_roles: str):
    """Dependency that checks if the current user has one of the allowed roles."""
    async def _checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Requires role: {', '.join(allowed_roles)}")
        return user
    return _checker


def require_minimum_role(minimum_role: str):
    """Dependency that checks if the user's role level meets a minimum threshold."""
    async def _checker(user: dict = Depends(get_current_user)):
        if not has_role_level(user.get("role", "viewer"), minimum_role):
            raise HTTPException(
                status_code=403,
                detail=f"Requires at least '{minimum_role}' role. Your role: '{user.get('role')}'"
            )
        return user
    return _checker


def require_permission(permission: str):
    """Dependency that checks if the user has a specific permission."""
    async def _checker(user: dict = Depends(get_current_user)):
        user_role = user.get("role", "viewer")
        if not has_permission(user_role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Missing permission: '{permission}'. Your role: '{user_role}'"
            )
        return user
    return _checker


def require_tier(*allowed_tiers: str):
    """Dependency that checks if the user's subscription tier allows access."""
    async def _checker(user: dict = Depends(get_current_user)):
        if user.get("tier") not in allowed_tiers:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires: {', '.join(allowed_tiers)} tier. Upgrade at /dashboard/settings."
            )
        return user
    return _checker


def require_org_membership():
    """Dependency that ensures the user belongs to an organization."""
    async def _checker(user: dict = Depends(get_current_user)):
        if not user.get("org_id"):
            raise HTTPException(
                status_code=403,
                detail="This feature requires organization membership. Create or join an organization first."
            )
        return user
    return _checker


# ═══════════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ═══════════════════════════════════════════════════════════════════

FEATURE_TIERS = {
    # MVP (free tier)
    "create_idea": ["free", "pro", "enterprise"],
    "single_agent": ["free", "pro", "enterprise"],
    "basic_workflow": ["free", "pro", "enterprise"],
    "view_reports": ["free", "pro", "enterprise"],

    # Pro tier
    "full_workflow": ["pro", "enterprise"],
    "pitch_simulation": ["pro", "enterprise"],
    "export_reports": ["pro", "enterprise"],
    "custom_agents": ["pro", "enterprise"],
    "compare_ideas": ["pro", "enterprise"],
    "analytics_dashboard": ["pro", "enterprise"],

    # Enterprise tier
    "team_collaboration": ["enterprise"],
    "api_access": ["enterprise"],
    "custom_investors": ["enterprise"],
    "white_label": ["enterprise"],
    "priority_processing": ["enterprise"],
    "sso_auth": ["enterprise"],
    "audit_trail": ["enterprise"],
    "org_management": ["enterprise"],
    "multi_workspace": ["enterprise"],
}


def require_feature(feature: str):
    """Dependency that checks if the user's tier includes the requested feature."""
    async def _checker(user: dict = Depends(get_current_user)):
        allowed_tiers = FEATURE_TIERS.get(feature, [])
        user_tier = user.get("tier", "free")
        if user_tier not in allowed_tiers:
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature}' requires upgrade. Available in: {', '.join(allowed_tiers)}"
            )
        return user
    return _checker


# ═══════════════════════════════════════════════════════════════════
# AUDIT LOGGING
# ═══════════════════════════════════════════════════════════════════

async def log_audit_event(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    org_id: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
) -> None:
    """Log an action to the audit trail for compliance and security."""
    try:
        from app.models.database import get_db_service
        db = get_db_service()

        entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "organization_id": org_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": None,
            "user_agent": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if request:
            forwarded = request.headers.get("x-forwarded-for")
            entry["ip_address"] = (
                forwarded.split(",")[0].strip() if forwarded
                else (request.client.host if request.client else None)
            )
            entry["user_agent"] = request.headers.get("user-agent", "")[:200]

        db._client.table("audit_log").insert(entry).execute()
        logger.debug("Audit event logged", action=action, resource=resource_type)
    except Exception as e:
        logger.warning("Audit logging failed", error=str(e))
