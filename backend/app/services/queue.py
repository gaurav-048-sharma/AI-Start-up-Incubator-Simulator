"""
Celery task queue for long-running AI agent workloads.
Offloads CrewAI/LangGraph execution from the web process.
Falls back to FastAPI BackgroundTasks when Celery/Redis is unavailable.
"""

import structlog
from typing import Any

logger = structlog.get_logger()

# Try to import Celery — graceful fallback
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None


def create_celery_app() -> Any:
    """Create and configure the Celery application."""
    if not CELERY_AVAILABLE:
        logger.warning("Celery not installed — using FastAPI BackgroundTasks instead")
        return None

    from app.config import get_settings
    settings = get_settings()
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")

    celery_app = Celery(
        "ai_incubator",
        broker=redis_url,
        backend=redis_url,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=600,       # 10 min hard limit
        task_soft_time_limit=540,  # 9 min soft limit
        worker_prefetch_multiplier=1,  # One task at a time (LLM calls are heavy)
        worker_max_tasks_per_child=50,  # Recycle workers to prevent memory leaks
        task_routes={
            "tasks.run_workflow": {"queue": "ai_heavy"},
            "tasks.run_simulation": {"queue": "ai_heavy"},
            "tasks.run_single_agent": {"queue": "ai_light"},
        },
    )

    return celery_app


# ── Task Definitions ─────────────────────────────────────────────

celery_app = create_celery_app()

if celery_app:
    @celery_app.task(name="tasks.run_workflow", bind=True, max_retries=2)
    def run_workflow_task(self, idea: dict, user_id: str):
        """Run the full incubation workflow as a Celery task."""
        import asyncio
        from app.workflows.graph import run_incubation_workflow
        from app.models.database import get_db_service

        async def _run():
            db = get_db_service()
            idea_id = idea.get("id", "")
            try:
                await db.update_idea(idea_id, {"status": "researching", "progress": 10})
                result = await run_incubation_workflow(idea, user_id)
                await db.update_idea(idea_id, {
                    "status": result.get("status", "completed"),
                    "progress": 100,
                })
                return {"status": "completed", "idea_id": idea_id}
            except Exception as e:
                logger.error("Celery workflow failed", idea_id=idea_id, error=str(e))
                await db.update_idea(idea_id, {"status": "failed", "progress": 0})
                raise self.retry(exc=e, countdown=30)

        return asyncio.run(_run())

    @celery_app.task(name="tasks.run_simulation", bind=True, max_retries=1)
    def run_simulation_task(self, idea_id: str, idea: dict, exec_summary: str, financial: str):
        """Run an investor pitch simulation as a Celery task."""
        import asyncio
        from app.simulation.pitch_engine import PitchEngine

        async def _run():
            engine = PitchEngine()
            return await engine.run_pitch(
                idea=idea,
                executive_summary=exec_summary,
                financial_projection=financial,
            )

        return asyncio.run(_run())


def dispatch_workflow(idea: dict, user_id: str):
    """
    Smart dispatcher: uses Celery if available, otherwise FastAPI BackgroundTasks.
    Returns a task ID if Celery, or None for background tasks.
    """
    if celery_app:
        result = run_workflow_task.delay(idea, user_id)
        logger.info("Dispatched workflow to Celery", task_id=result.id, idea_id=idea.get("id"))
        return result.id
    return None
