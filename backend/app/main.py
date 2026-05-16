"""
FastAPI application entry point for the AI Start-up Incubator Simulator.
Configures CORS, routes, WebSocket endpoints, and application lifecycle.
"""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config import get_settings
from app.api.routes import ideas, agents, workflows, simulation, reports
from app.api.websockets import router as ws_router

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
    yield
    logger.info("Shutting down AI Incubator Engine")


def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered startup incubator — research, validate, and pitch startup ideas with autonomous agents.",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # ── CORS ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routes ───────────────────────────────────────────────
    app.include_router(ideas.router, prefix="/api/ideas", tags=["Ideas"])
    app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
    app.include_router(workflows.router, prefix="/api/workflows", tags=["Workflows"])
    app.include_router(simulation.router, prefix="/api/simulations", tags=["Simulations"])
    app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
    app.include_router(ws_router, tags=["WebSocket"])

    # ── Health Check ─────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
            "services": {
                "openai": settings.has_openai,
                "anthropic": settings.has_anthropic,
                "supabase": settings.has_supabase,
                "tavily": settings.has_tavily,
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
