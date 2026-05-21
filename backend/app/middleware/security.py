"""
Security middleware stack for the AI Incubator backend.
Provides: rate limiting, request correlation IDs, JWT auth, separated
platform/tenant RBAC, multi-tenant org context via X-Org-Id header,
audit logging, and feature gating.

Architecture:
  - Platform Roles  (profiles.platform_role): super_admin, support, billing_admin, user
  - Tenant Roles    (organization_members.role): admin, incubator_manager, founder, team_member, viewer, etc.
  - These are NEVER merged. A user who is "admin" in Org A has zero platform-wide privileges.
"""

import uuid
import time
import structlog
from collections import defaultdict
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
from datetime import datetime, timezone
import contextvars

# note: `asyncio`, `get_settings`, and `get_supabase_client` are imported locally where needed

# ── Caching Layer ────────────────────────────────────────────────
# Caching role data for 60 seconds to avoid multi-second DB latency
_PROFILE_CACHE: dict[str, dict] = {} # {user_id: {"data": {...}, "expires": float}}
_CACHE_TTL = 60.0

# Global context for passing JWT to the database service
current_jwt: contextvars.ContextVar[str] = contextvars.ContextVar("current_jwt", default="")

logger = structlog.get_logger()

def invalidate_profile_cache(user_id: str):
    """Force validation of platform role on the next request."""
    if user_id in _PROFILE_CACHE:
        del _PROFILE_CACHE[user_id]
        


# ═══════════════════════════════════════════════════════════════════
# PLATFORM ROLES — global system-level access
# ═══════════════════════════════════════════════════════════════════

PLATFORM_ROLES = {
    "user":          0,
    "support":       50,
    "billing_admin": 60,
    "super_admin":   100,
}

PLATFORM_ROLE_DESCRIPTIONS = {
    "user":          "Regular application user with no platform privileges",
    "support":       "Read-only global visibility for troubleshooting",
    "billing_admin": "Manages platform billing, subscriptions, and revenue",
    "super_admin":   "Full platform operations: migrations, feature flags, org suspension",
}


# ═══════════════════════════════════════════════════════════════════
# TENANT ROLES — per-organization access (NEVER elevate to platform)
# ═══════════════════════════════════════════════════════════════════

WORKSPACE_OWNER_ROLE = "workspace_owner"

TENANT_ROLE_HIERARCHY = {
    "viewer":                10,
    "team_member":           20,
    "ui_ux_designer":        20,
    "fullstack_engineer":    20,
    "backend_engineer":      20,
    "devops_engineer":       20,
    "ai_engineer":           25,
    "security_consultant":   25,
    "growth_marketing_lead": 25,
    "founder_product_lead":  30,
    "founder":               30,
    "investor_advisor":      40,
    "innovation_lead":       50,
    "incubator_manager":     60,
    "admin":                 70,
    WORKSPACE_OWNER_ROLE:     80,
}

ASSIGNABLE_TENANT_ROLES = {
    role for role in TENANT_ROLE_HIERARCHY
    if role != WORKSPACE_OWNER_ROLE
}

# Legacy alias for backwards-compatible imports.
# CRITICAL: super_admin is a PLATFORM role, NEVER a tenant role.
# It must NOT appear in this hierarchy to prevent privilege escalation
# (e.g. a rogue org admin assigning 'super_admin' as a tenant role).
ROLE_HIERARCHY = {**TENANT_ROLE_HIERARCHY}

ROLE_DESCRIPTIONS = {
    "viewer":                "Read-only access to shared ideas and reports",
    "team_member":           "Collaborate on ideas, view reports, contribute to workflows",
    "ui_ux_designer":        "Focus on user experience, interfaces, and product design prototypes",
    "fullstack_engineer":    "Build and deploy full-stack implementations of startup ideas",
    "backend_engineer":      "Design backend architectures, databases, and APIs",
    "devops_engineer":       "Manage deployments, infrastructure, and CI/CD pipelines",
    "ai_engineer":           "Integrate ML models, design AI workflows and agent interactions",
    "security_consultant":   "Review architectures for vulnerabilities and compliance",
    "growth_marketing_lead": "Analyze market fit, growth strategies, and marketing reports",
    "founder_product_lead":  "Lead product vision, manage own ideas, simulations, and team",
    "founder":               "Full access to own ideas, simulations, reports, and subscriptions",
    "investor_advisor":      "Review startup simulations, provide feedback, access pitch data",
    "innovation_lead":       "Manage internal projects, organizational teams, white-label settings",
    "incubator_manager":     "Org admin: manage users, SSO, and all workflows in the workspace",
    "admin":                 "Org admin: manage users, SSO, billing, and workspace settings",
    "workspace_owner":       "Workspace owner: billing authority and ultimate org accountability",
    "super_admin":           "Platform super admin (platform_role, not a tenant role)",
}

# ── Tenant Permissions ───────────────────────────────────────────

ROLE_PERMISSIONS = {
    "viewer": [
        "view_ideas", "view_reports", "view_workflows",
    ],
    "team_member": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "view_agents",
    ],
    "ui_ux_designer": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "view_agents",
    ],
    "fullstack_engineer": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "view_agents",
    ],
    "backend_engineer": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "view_agents",
    ],
    "devops_engineer": [
        "view_ideas", "view_reports", "view_workflows",
        "view_agents", "view_analytics",
    ],
    "ai_engineer": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "view_agents", "run_simulation",
    ],
    "security_consultant": [
        "view_ideas", "view_reports", "view_workflows",
        "view_audit_log",
    ],
    "growth_marketing_lead": [
        "view_ideas", "view_reports", "view_workflows",
        "view_analytics", "export_reports",
    ],
    "founder_product_lead": [
        "view_ideas", "view_reports", "view_workflows",
        "create_idea", "edit_own_ideas", "view_agents",
        "launch_workflow", "run_simulation", "view_analytics",
        "manage_own_settings", "export_reports",
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
}

ROLE_PERMISSIONS[WORKSPACE_OWNER_ROLE] = list(ROLE_PERMISSIONS["admin"])


def has_permission(user_role: str, required_permission: str) -> bool:
    """Check if a TENANT role has a specific permission.
    
    IMPORTANT: This function ONLY checks tenant roles.
    Platform super_admin bypass is handled by the calling dependency
    (require_permission, require_minimum_role, etc.).
    Never pass platform_role to this function.
    """
    perms = ROLE_PERMISSIONS.get(user_role, [])
    return required_permission in perms


def has_role_level(user_role: str, minimum_role: str) -> bool:
    """Check if a TENANT role level meets or exceeds the minimum.
    
    Uses TENANT_ROLE_HIERARCHY only. Platform roles are never
    compared here — super_admin bypass is in the calling dependency.
    """
    user_level = TENANT_ROLE_HIERARCHY.get(user_role, 0)
    min_level = TENANT_ROLE_HIERARCHY.get(minimum_role, 999)
    return user_level >= min_level


def resolve_effective_org_role(user: dict) -> str:
    """Resolve the effective tenant role for permission checks."""
    return user.get("org_role") or user.get("role", "viewer")


def has_platform_level(platform_role: str, minimum: str) -> bool:
    """Check if user's platform role meets the minimum."""
    user_level = PLATFORM_ROLES.get(platform_role, 0)
    min_level = PLATFORM_ROLES.get(minimum, 999)
    return user_level >= min_level


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter.
    Applies stricter limits to unauthenticated/public endpoints.
    For production, replace with Redis-backed SlowAPI.
    """

    # Public endpoints that get a stricter rate limit
    STRICT_PATHS = {
        "/api/admin/request": 5,     # 5 requests/min for public enterprise request submissions
        "/api/enterprise/request": 5, # Legacy alias
    }

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
        if request.url.path in ("/health", "/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)
        if request.url.path.startswith("/ws/"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()

        # Apply stricter limits to public/unauthenticated endpoints
        effective_rpm = self.STRICT_PATHS.get(request.url.path, self.rpm)

        # Use a separate bucket key for strict endpoints to prevent
        # normal API usage from consuming the tight public budget
        bucket_key = f"{client_ip}:{request.url.path}" if request.url.path in self.STRICT_PATHS else client_ip

        self._clean_window(bucket_key, now)

        if len(self._windows[bucket_key]) >= effective_rpm:
            logger.warning("Rate limit exceeded", client_ip=client_ip, path=request.url.path, limit=effective_rpm)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "detail": f"Max {effective_rpm} requests per minute"},
                headers={"Retry-After": "60"},
            )

        self._windows[bucket_key].append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(effective_rpm)
        response.headers["X-RateLimit-Remaining"] = str(effective_rpm - len(self._windows[bucket_key]))
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds a unique X-Request-ID header to every request for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


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


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Injects tenant context defaults into request.state.
    The actual org resolution is performed in get_current_user() via
    the X-Org-Id header. This middleware ensures request.state fields
    are always initialised for downstream middleware/handlers.
    """

    async def dispatch(self, request: Request, call_next):
        # Initialize defaults so downstream code can always access these
        request.state.org_id = None
        request.state.org_role = None
        request.state.org_status = None
        request.state.org_read_only = False
        response = await call_next(request)
        return response


# ═══════════════════════════════════════════════════════════════════
# AUTH DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """
    Validates the Supabase JWT and returns the user payload.
    
    Returns dict with SEPARATED scopes:
      - id, email, full_name      — identity
      - platform_role             — system-wide role (user/support/billing_admin/super_admin)
      - tier                      — subscription tier (free/pro/enterprise)
      - org_id                    — active tenant from X-Org-Id header
      - org_role                  — role WITHIN that tenant (admin/founder/viewer/etc.)
    
    CRITICAL: org_role never elevates platform_role or vice versa.
    """
    from app.config import get_settings
    settings = get_settings()

    # Demo mode
    if not settings.has_supabase:
        # Demo user for local development and tests — provide a demo org context
        return {
            "id": "demo-user",
            "email": "demo@incubator.ai",
            "platform_role": "user",
            "tier": "free",
            "org_id": "demo-org",
            "org_role": "founder",
            "full_name": "Demo Founder",
            # Legacy compat
            "role": "founder",
        }

    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    current_jwt.set(credentials.credentials)

    try:
        import asyncio
        from app.models.database import get_supabase_client
        supabase = get_supabase_client(admin=True)
        if not supabase:
            logger.error("Database client initialization failed")
            raise HTTPException(status_code=500, detail="Database not configured")

        if not credentials or not credentials.credentials:
            raise HTTPException(status_code=401, detail="Missing authentication token")

        # Use the admin client to get user details
        try:
            user_response = await asyncio.to_thread(supabase.auth.get_user, credentials.credentials)
        except Exception as auth_err:
            logger.error("Supabase auth.get_user failed", error=str(auth_err))
            raise HTTPException(status_code=401, detail=f"Invalid or expired session: {str(auth_err)}")

        if not user_response or not user_response.user:
            logger.warning("No user found in Supabase session")
            raise HTTPException(status_code=401, detail="User session not found or has been revoked")

        user = user_response.user
        user_id = str(user.id)

        # user_metadata/app_metadata can be arbitrary JSON values; coerce to dict for safe .get() usage
        raw_user_meta = getattr(user, "user_metadata", None) or {}
        user_meta = raw_user_meta if isinstance(raw_user_meta, dict) else {}
        user_tier = user_meta.get("tier", "free")

        # MFA Context: Authenticator Assurance Level (aal1 = password, aal2 = MFA)
        raw_app_meta = getattr(user, "app_metadata", None) or {}
        auth_app_metadata = raw_app_meta if isinstance(raw_app_meta, dict) else {}
        aal = auth_app_metadata.get("aal", "aal1")

        # Fetch platform_role from profiles (with caching)
        platform_role = user_meta.get("platform_role", "user")
        profile_role = user_meta.get("role", "founder")
        
        now = time.time()
        cached = _PROFILE_CACHE.get(user_id)
        
        if cached and cached["expires"] > now:
            p_data = cached["data"]
            platform_role = p_data.get("platform_role", platform_role)
            profile_role = p_data.get("role", profile_role)
            user_tier = p_data.get("tier", user_tier)
        else:
            try:
                db_client = get_supabase_client(admin=True)
                profile = await asyncio.to_thread(
                    lambda: db_client.table("profiles")
                    .select("platform_role, role, tier")
                    .eq("id", user_id)
                    .single()
                    .execute()
                )
                if profile.data and isinstance(profile.data, dict):
                    platform_role = profile.data.get("platform_role") or platform_role
                    profile_role = profile.data.get("role") or profile_role
                    user_tier = profile.data.get("tier") or user_tier
                    # Cache it
                    _PROFILE_CACHE[user_id] = {
                        "data": {
                            "platform_role": platform_role,
                            "role": profile_role,
                            "tier": user_tier
                        },
                        "expires": now + _CACHE_TTL
                    }
            except Exception as e:
                logger.warning("Profile enrichment failed", error=str(e), user_id=user_id)

        # Resolve tenant context from X-Org-Id header
        org_id = request.headers.get("x-org-id")
        if org_id == "": # Handle empty string from frontend
            org_id = None
        org_role = None
        is_owner = False
        org_read_only = False

        # Super Admins only resolve org context if they explicitly provide it.
        # They are NOT restricted by memberships.
        if platform_role == "super_admin":
            if org_id:
                # If they select an org, they get 'admin' role in that context
                org_role = "admin"
            return {
                "id": user_id,
                "email": user.email,
                "platform_role": platform_role,
                "tier": user_tier,
                "org_id": org_id,
                "org_role": org_role,
                "org_owner": False,
                "org_read_only": False,
                "mfa_active": aal == "aal2",
                "mfa_aal": aal,
                "full_name": user_meta.get("full_name", ""),
                "role": profile_role,
            }

        if org_id:
            try:
                # Fetch org details + membership in a single pass where possible
                org_details = await asyncio.to_thread(
                    lambda: supabase.table("organizations")
                    .select("owner_id, status, subscription_status")
                    .eq("id", org_id)
                    .single()
                    .execute()
                )

                # ── Org status enforcement ──────────────────────────
                if org_details.data and isinstance(org_details.data, dict):
                    org_status = org_details.data.get("status", "active")
                    sub_status = org_details.data.get("subscription_status", "active")

                    if org_status == "suspended" and platform_role != "super_admin":
                        raise HTTPException(
                            status_code=403,
                            detail="This organization has been suspended. Contact your administrator.",
                        )

                    if sub_status in ("canceled", "past_due", "suspended"):
                        org_read_only = True

                    if org_details.data.get("owner_id") == user_id:
                        is_owner = True

                # Resolve membership
                membership = await asyncio.to_thread(
                    lambda: supabase.table("organization_members")
                    .select("role")
                    .eq("organization_id", org_id)
                    .eq("user_id", user_id)
                    .single()
                    .execute()
                )
                if membership.data and isinstance(membership.data, dict):
                    org_role = membership.data.get("role")
                    if is_owner:
                        org_role = WORKSPACE_OWNER_ROLE
                elif is_owner:
                    org_role = WORKSPACE_OWNER_ROLE
                else:
                    # Regular user tried to access an org they don't belong to
                    org_id = None
                    org_read_only = False
            except HTTPException:
                raise
            except Exception:
                org_id = None

        return {
            "id": user_id,
            "email": user.email,
            "platform_role": platform_role,
            "tier": user_tier,
            "org_id": org_id,
            "org_role": org_role,
            "org_owner": is_owner,
            "org_read_only": org_read_only,
            "mfa_active": aal == "aal2",
            "mfa_aal": aal,
            "full_name": user_meta.get("full_name", ""),
            # Legacy compat — the user's profile role (NOT platform scope)
            "role": profile_role,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Auth validation failed", error=str(e))
        raise HTTPException(status_code=401, detail="Authentication failed")


# ═══════════════════════════════════════════════════════════════════
# RBAC DEPENDENCIES — PLATFORM SCOPE
# ═══════════════════════════════════════════════════════════════════

def require_platform_role(minimum_role: str):
    """
    Dependency that checks the user's PLATFORM role.
    Use this for global admin endpoints (enterprise management, org listing, etc.)
    """
    async def _checker(user: dict = Depends(get_current_user)):
        if not has_platform_level(user.get("platform_role", "user"), minimum_role):
            raise HTTPException(
                status_code=403,
                detail=f"Platform role '{minimum_role}' required. Your platform role: '{user.get('platform_role', 'user')}'"
            )
        return user
    return _checker


# ═══════════════════════════════════════════════════════════════════
# RBAC DEPENDENCIES — TENANT SCOPE
# ═══════════════════════════════════════════════════════════════════

def require_role(*allowed_roles: str):
    """Dependency that checks if the current user has one of the allowed tenant roles."""
    async def _checker(user: dict = Depends(get_current_user)):
        effective = resolve_effective_org_role(user)
        if effective not in allowed_roles and user.get("platform_role") != "super_admin":
            raise HTTPException(status_code=403, detail=f"Requires role: {', '.join(allowed_roles)}")
        return user
    return _checker


def require_minimum_role(minimum_role: str):
    """
    Dependency that checks if the user's TENANT role level meets a minimum threshold.
    Also validates IDOR: if the path contains {org_id}, the user must belong to THAT org.
    Platform super_admins bypass tenant checks.
    """
    async def _checker(request: Request, user: dict = Depends(get_current_user)):
        # Platform super_admins bypass tenant-level checks
        if user.get("platform_role") == "super_admin":
            return user
        
        target_org = request.path_params.get("org_id")

        # IDOR protection: path org_id must match the user's active org context
        if target_org:
            if user.get("org_id") != target_org:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: you are not a member of this organization."
                )

        # Determine effective tenant role
        effective_role = resolve_effective_org_role(user)

        if not has_role_level(effective_role, minimum_role):
            raise HTTPException(
                status_code=403,
                detail=f"Requires at least '{minimum_role}' role. Your effective role: '{effective_role}'"
            )
        return user
    return _checker


def require_permission(permission: str):
    """Dependency that checks if the user has a specific tenant permission."""
    async def _checker(request: Request, user: dict = Depends(get_current_user)):
        # Platform super_admins have all permissions
        if user.get("platform_role") == "super_admin":
            return user

        target_org = request.path_params.get("org_id")

        # IDOR protection
        if target_org:
            if user.get("org_id") != target_org:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: you are not a member of this organization."
                )

        effective_role = resolve_effective_org_role(user)

        if not has_permission(effective_role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Missing permission: '{permission}'. Your effective role: '{effective_role}'"
            )
        return user
    return _checker


def require_tier(*allowed_tiers: str):
    """Dependency that checks if the user's subscription tier allows access."""
    async def _checker(user: dict = Depends(get_current_user)):
        # SUPER ADMIN EXEMPTION
        if user.get("platform_role") == "super_admin":
            return user
        if user.get("tier") not in allowed_tiers:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires: {', '.join(allowed_tiers)} tier. Upgrade at /dashboard/settings."
            )
        return user
    return _checker


def require_org_context():
    """
    Dependency that ensures a valid X-Org-Id header was provided and resolved.
    Use this on any endpoint that operates within a tenant workspace.
    """
    async def _checker(user: dict = Depends(get_current_user)):
        if not user.get("org_id") and user.get("platform_role") != "super_admin":
            raise HTTPException(
                status_code=403,
                detail="X-Org-Id header required. Select an organization context."
            )
        return user
    return _checker


def require_write_access():
    """
    Dependency that blocks write operations when the org is in read-only mode.
    Used for endpoints that modify org data (create ideas, update settings, etc.)
    when subscription_status is 'past_due' or 'canceled'.
    """
    async def _checker(user: dict = Depends(get_current_user)):
        if user.get("org_read_only") and user.get("platform_role") != "super_admin":
            raise HTTPException(
                status_code=403,
                detail="This organization's subscription is past due or canceled. "
                       "Write operations are disabled. Please update your billing information."
            )
        return user
    return _checker


def require_mfa_stepup():
    """
    Dependency that enforces MFA step-up for privileged roles.
    Blocked roles: platform super_admin, platform billing_admin, tenant admin.
    These roles MUST have an aal2 session to access the endpoint.
    Dependency that enforces aal2 (MFA) session.
    Bypassed in development mode for easier testing.
    """
    async def _checker(user: dict = Depends(get_current_user)):
        from app.config import get_settings
        settings = get_settings()
        
        # Bypass MFA in development for improved developer experience
        if settings.debug or settings.environment == "development":
            return user
            
        if not user.get("mfa_active"):
            logger.warning("MFA step-up required for privileged access", 
                           user_id=user["id"], role=user.get("platform_role"))
            raise HTTPException(
                status_code=403,
                detail="MFA required. Please complete a second-factor challenge."
            )
        return user
    return _checker


def require_org_membership():
    """Dependency that ensures the user belongs to an organization (backward compat)."""
    return require_org_context()


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
        from app.config import get_settings
        settings = get_settings()
        # In demo/development mode, enable features for easier testing
        if not settings.has_supabase or settings.debug or settings.environment == "development":
            return user

        if user.get("platform_role") == "super_admin":
            return user
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
