"""
Supabase database client and helper functions.
Provides typed access to all database tables with error handling.
"""

import structlog
from typing import Optional, Any
from supabase import create_client, Client

from app.config import get_settings

logger = structlog.get_logger()

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Get or create the Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        if not settings.has_supabase:
            logger.warning("Supabase not configured — using mock mode")
            return None
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key or settings.supabase_anon_key,
        )
        logger.info("Supabase client initialized")
    return _supabase_client


class DatabaseService:
    """High-level database operations for the incubator platform."""

    def __init__(self):
        self._client = get_supabase_client()

    # ── Profiles ─────────────────────────────────────────────────

    async def get_profile(self, user_id: str) -> Optional[dict]:
        """Get a user profile by ID."""
        try:
            result = self._client.table("profiles").select("*").eq("id", user_id).single().execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get profile", user_id=user_id, error=str(e))
            return None

    async def update_profile(self, user_id: str, data: dict) -> Optional[dict]:
        """Update a user profile."""
        try:
            result = self._client.table("profiles").update(data).eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Failed to update profile", user_id=user_id, error=str(e))
            return None

    # ── Ideas ────────────────────────────────────────────────────

    async def create_idea(self, idea_data: dict) -> Optional[dict]:
        """Create a new startup idea."""
        try:
            import asyncio
            result = await asyncio.to_thread(
                lambda: self._client.table("ideas").insert(idea_data).execute()
            )
            logger.info("Idea created", idea_id=result.data[0]["id"])
            return result.data[0]
        except Exception as e:
            logger.error("Failed to create idea", error=str(e))
            return None

    async def get_idea(self, idea_id: str) -> Optional[dict]:
        """Get a startup idea by ID."""
        try:
            import asyncio
            result = await asyncio.to_thread(
                lambda: self._client.table("ideas").select("*").eq("id", idea_id).single().execute()
            )
            return result.data
        except Exception as e:
            logger.error("Failed to get idea", idea_id=idea_id, error=str(e))
            return None

    async def get_user_ideas(self, user_id: str) -> list[dict]:
        """Get all ideas for a user."""
        try:
            import asyncio
            result = await asyncio.to_thread(
                lambda: self._client.table("ideas")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("Failed to get user ideas", user_id=user_id, error=str(e))
            return []

    async def update_idea(self, idea_id: str, data: dict) -> Optional[dict]:
        """Update a startup idea."""
        try:
            import asyncio
            result = await asyncio.to_thread(
                lambda: self._client.table("ideas").update(data).eq("id", idea_id).execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Failed to update idea", idea_id=idea_id, error=str(e))
            return None

    async def delete_idea(self, idea_id: str) -> bool:
        """Delete a startup idea."""
        try:
            self._client.table("ideas").delete().eq("id", idea_id).execute()
            logger.info("Idea deleted", idea_id=idea_id)
            return True
        except Exception as e:
            logger.error("Failed to delete idea", idea_id=idea_id, error=str(e))
            return False

    # ── Agent Activities ─────────────────────────────────────────

    async def log_agent_activity(self, activity_data: dict) -> Optional[dict]:
        """Log an agent activity event."""
        try:
            result = self._client.table("agent_activities").insert(activity_data).execute()
            return result.data[0]
        except Exception as e:
            logger.error("Failed to log agent activity", error=str(e))
            return None

    async def get_idea_activities(self, idea_id: str) -> list[dict]:
        """Get all agent activities for an idea."""
        try:
            result = (
                self._client.table("agent_activities")
                .select("*")
                .eq("idea_id", idea_id)
                .order("started_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("Failed to get activities", idea_id=idea_id, error=str(e))
            return []

    async def update_agent_activity(self, activity_id: str, data: dict) -> Optional[dict]:
        """Update an agent activity record."""
        try:
            result = (
                self._client.table("agent_activities")
                .update(data)
                .eq("id", activity_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Failed to update activity", activity_id=activity_id, error=str(e))
            return None

    # ── Workflow States ──────────────────────────────────────────

    async def save_workflow_state(self, state_data: dict) -> Optional[dict]:
        """Save or update a workflow state."""
        try:
            result = self._client.table("workflow_states").upsert(state_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Failed to save workflow state", error=str(e))
            return None

    async def get_workflow_state(self, idea_id: str) -> Optional[dict]:
        """Get the latest workflow state for an idea."""
        try:
            result = (
                self._client.table("workflow_states")
                .select("*")
                .eq("idea_id", idea_id)
                .order("updated_at", desc=True)
                .limit(1)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error("Failed to get workflow state", idea_id=idea_id, error=str(e))
            return None

    # ── Reports ──────────────────────────────────────────────────

    async def create_report(self, report_data: dict) -> Optional[dict]:
        """Create a new report."""
        try:
            result = self._client.table("reports").insert(report_data).execute()
            logger.info("Report created", report_id=result.data[0]["id"])
            return result.data[0]
        except Exception as e:
            logger.error("Failed to create report", error=str(e))
            return None

    async def get_idea_reports(self, idea_id: str) -> list[dict]:
        """Get all reports for an idea."""
        try:
            result = (
                self._client.table("reports")
                .select("*")
                .eq("idea_id", idea_id)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("Failed to get reports", idea_id=idea_id, error=str(e))
            return []

    async def get_report(self, report_id: str) -> Optional[dict]:
        """Get a specific report."""
        try:
            result = self._client.table("reports").select("*").eq("id", report_id).single().execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get report", report_id=report_id, error=str(e))
            return None

    # ── Simulations ──────────────────────────────────────────────

    async def create_simulation(self, sim_data: dict) -> Optional[dict]:
        """Create a new simulation record."""
        try:
            result = self._client.table("simulations").insert(sim_data).execute()
            logger.info("Simulation created", sim_id=result.data[0]["id"])
            return result.data[0]
        except Exception as e:
            logger.error("Failed to create simulation", error=str(e))
            return None

    async def get_simulation(self, sim_id: str) -> Optional[dict]:
        """Get a simulation by ID."""
        try:
            result = self._client.table("simulations").select("*").eq("id", sim_id).single().execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get simulation", sim_id=sim_id, error=str(e))
            return None

    async def update_simulation(self, sim_id: str, data: dict) -> Optional[dict]:
        """Update a simulation record."""
        try:
            result = self._client.table("simulations").update(data).eq("id", sim_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Failed to update simulation", sim_id=sim_id, error=str(e))
            return None

    async def get_idea_simulations(self, idea_id: str) -> list[dict]:
        """Get all simulations for an idea."""
        try:
            result = (
                self._client.table("simulations")
                .select("*")
                .eq("idea_id", idea_id)
                .order("started_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("Failed to get simulations", idea_id=idea_id, error=str(e))
            return []


_db_service: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    """Get or create the global database service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
