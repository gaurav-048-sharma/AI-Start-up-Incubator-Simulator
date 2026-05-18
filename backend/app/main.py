"""
FastAPI application entry point for the AI Start-up Incubator Simulator.
Configures CORS, security middleware, routes, WebSocket endpoints, and application lifecycle.
"""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import ideas, agents, workflows, simulation, reports
from app.api.routes import analytics, notifications, settings as settings_routes, comparison
from app.api.routes import organizations as org_routes, enterprise
from app.api.websockets import router as ws_router
from app.middleware.security import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info(
        "Starting AI Incubator Engine",
        version=settings.app_version,
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        supabase_connected=settings.has_supabase,
    )

    # Initialize Redis cache (optional)
    try:
        from app.services.cache import get_cache
        cache = get_cache()
        await cache.connect()
        app.state.cache = cache
    except Exception as e:
        logger.warning("Redis cache not available", error=str(e))

    # Initialize Sentry (optional)
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.starlette import StarletteIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=0.3 if settings.environment == "production" else 1.0,
                environment=settings.environment,
                release=settings.app_version,
                integrations=[FastApiIntegration(), StarletteIntegration()],
            )
            logger.info("Sentry initialized", environment=settings.environment)
        except ImportError:
            logger.warning("sentry-sdk not installed — error tracking disabled")

    yield

    # Shutdown
    try:
        if hasattr(app.state, "cache") and app.state.cache:
            await app.state.cache.disconnect()
    except Exception:
        pass

    logger.info("Shutting down AI Incubator Engine")


def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered startup incubator — research, validate, and pitch startup ideas with autonomous agents.",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # ── Security Middleware (order matters — outermost first) ────
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_rpm,
    )

    # ── CORS ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time", "X-RateLimit-Remaining"],
    )

    # ── API Routes ───────────────────────────────────────────────
    app.include_router(ideas.router, prefix="/api/ideas", tags=["Ideas"])
    app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
    app.include_router(workflows.router, prefix="/api/workflows", tags=["Workflows"])
    app.include_router(simulation.router, prefix="/api/simulations", tags=["Simulations"])
    app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
    app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
    app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])
    app.include_router(comparison.router, prefix="/api/ideas", tags=["Comparison"])
    app.include_router(org_routes.router, prefix="/api/organizations", tags=["Organizations"])
    app.include_router(enterprise.router, prefix="/api/enterprise", tags=["Enterprise"])
    app.include_router(ws_router, tags=["WebSocket"])

    # ── Billing Routes (plans always available, checkout needs Stripe) ─
    try:
        from app.api.routes.billing import router as billing_router
        app.include_router(billing_router, prefix="/api/billing", tags=["Billing"])
    except ImportError:
        logger.warning("Billing routes not available")

    # ── Prometheus Metrics Endpoint ──────────────────────────────
    @app.get("/metrics", tags=["System"], include_in_schema=False)
    async def metrics():
        """Prometheus-compatible metrics endpoint."""
        from app.services.cache import get_cache
        cache = get_cache()
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "cache_connected": cache.is_connected,
        }

    # ── Health Check ─────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        from app.services.cache import get_cache
        cache = get_cache()
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
            "services": {
                "openai": settings.has_openai,
                "anthropic": settings.has_anthropic,
                "supabase": settings.has_supabase,
                "tavily": settings.has_tavily,
                "redis": cache.is_connected,
                "sentry": bool(settings.sentry_dsn),
                "stripe": bool(settings.stripe_secret_key),
            },
        }

    @app.get("/", tags=["System"])
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs" if settings.debug else "Disabled in production",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
