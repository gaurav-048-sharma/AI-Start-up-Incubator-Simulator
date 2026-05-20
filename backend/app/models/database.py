"""
Supabase database client and helper functions.
Provides typed access to all database tables with error handling.
"""

import structlog
import httpx
import asyncio
from typing import Optional, Any
from supabase import create_client, Client

from app.config import get_settings

logger = structlog.get_logger()

_admin_supabase_client: Optional[Client] = None
_shared_httpx_client: Optional[httpx.AsyncClient] = None

def get_supabase_client(admin: bool = False) -> Client:
    """
    Get the Supabase client with connection pooling.
    """
    global _admin_supabase_client
    settings = get_settings()
    
    # If Supabase not configured, return None to enable demo/mock mode
    if not settings.has_supabase:
        return None

    if admin:
        if _admin_supabase_client is None:
            # We use the standard create_client but we can pass a custom session
            # if we really wanted to, but for now just the singleton is a huge win.
            _admin_supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )
        return _admin_supabase_client

    # Service role for backend (RBAC gated in middleware)
    key = settings.supabase_service_role_key
    
    from app.middleware.security import current_jwt
    try:
        token = current_jwt.get()
    except LookupError:
        token = ""

    options = None
    if token:
        from supabase.client import ClientOptions
        options = ClientOptions(headers={"Authorization": f"Bearer {token}"})
        
    return create_client(settings.supabase_url, key, options=options)


class DatabaseService:
    """High-level database operations for the incubator platform."""

    def __init__(self):
        pass

    @property
    def _client(self):
        return get_supabase_client()

    # ── Profiles ─────────────────────────────────────────────────

    async def get_profile(self, user_id: str) -> Optional[dict]:
        """Get a user profile by ID."""
        settings = get_settings()
        if not settings.has_supabase:
            # Demo environment: return a minimal profile
            return {"id": user_id, "platform_role": "user", "role": "founder", "tier": "free"}
        try:
            result = await asyncio.to_thread(
                lambda: self._client.table("profiles").select("*").eq("id", user_id).single().execute()
            )
            return result.data
        except Exception as e:
            if self._client is not None:
                logger.error("Failed to get profile", user_id=user_id, error=str(e))
            return None

    async def update_profile(self, user_id: str, data: dict) -> Optional[dict]:
        """Update a user profile."""
        settings = get_settings()
        if not settings.has_supabase:
            # Demo environment: merge and return
            profile = {"id": user_id, "platform_role": "user", "role": "founder", "tier": "free"}
            profile.update(data)
            return profile
        try:
            result = await asyncio.to_thread(
                lambda: self._client.table("profiles").update(data).eq("id", user_id).execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            if self._client is not None:
                logger.error("Failed to update profile", user_id=user_id, error=str(e))
            return None

    # ── Ideas ────────────────────────────────────────────────────

    async def create_idea(self, idea_data: dict) -> Optional[dict]:
        """Create a new startup idea."""
        settings = get_settings()
        if not settings.has_supabase:
            # Demo environment: return the provided idea_data as created
            logger.info("Idea created (demo)", idea_id=idea_data.get("id"))
            return idea_data
        try:
            result = await asyncio.to_thread(
                lambda: self._client.table("ideas").insert(idea_data).execute()
            )
            logger.info("Idea created", idea_id=result.data[0]["id"])
            return result.data[0]
        except Exception as e:
            if self._client is not None:
                logger.error("Failed to create idea", error=str(e))
            return None

    async def get_idea(self, idea_id: str) -> Optional[dict]:
        """Get a startup idea by ID."""
        settings = get_settings()
        if not settings.has_supabase:
            return None
        try:
            result = await asyncio.to_thread(
                lambda: self._client.table("ideas").select("*").eq("id", idea_id).single().execute()
            )
            return result.data
        except Exception as e:
            if self._client is not None:
                logger.error("Failed to get idea", idea_id=idea_id, error=str(e))
            return None

    async def get_user_ideas(self, user_id: str, organization_id: Optional[str] = None) -> list[dict]:
        """Get all ideas for a user or organization."""
        settings = get_settings()
        if not settings.has_supabase:
            return []
        try:
            def _execute_query():
                query = self._client.table("ideas").select("*")
                if organization_id:
                    query = query.eq("organization_id", organization_id)
                else:
                    query = query.eq("user_id", user_id)
                return query.order("created_at", desc=True).execute()

            result = await asyncio.to_thread(_execute_query)
            return result.data or []
        except Exception as e:
            if self._client is not None:
                logger.error("Failed to get ideas", user_id=user_id, org_id=organization_id, error=str(e))
            return []

    async def get_ideas(self, organization_id: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        """Get ideas scoped by organization or user."""
        settings = get_settings()
        if not settings.has_supabase:
            return {"ideas": [], "total": 0}
        try:
            def _execute_query():
                query = self._client.table("ideas").select("*")
                if organization_id:
                    query = query.eq("organization_id", organization_id)
                elif user_id:
                    query = query.eq("user_id", user_id)
                return query.order("created_at", desc=True).execute()

            result = await asyncio.to_thread(_execute_query)
            ideas = result.data or []
            return {"ideas": ideas, "total": len(ideas)}
        except Exception as e:
            if self._client is not None:
                logger.error("Failed to list ideas", user_id=user_id, org_id=organization_id, error=str(e))
            return {"ideas": [], "total": 0}

    async def update_idea(self, idea_id: str, data: dict) -> Optional[dict]:
        """Update a startup idea."""
        try:
            result = await asyncio.to_thread(
                lambda: self._client.table("ideas").update(data).eq("id", idea_id).execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            if self._client is not None:
                logger.error("Failed to update idea", idea_id=idea_id, error=str(e))
            return None

    async def delete_idea(self, idea_id: str) -> bool:
        """Delete a startup idea."""
        try:
            await asyncio.to_thread(
                lambda: self._client.table("ideas").delete().eq("id", idea_id).execute()
            )
            logger.info("Idea deleted", idea_id=idea_id)
            return True
        except Exception as e:
            if self._client is not None:
                logger.error("Failed to delete idea", idea_id=idea_id, error=str(e))
            return False

    # ── Agent Activities ─────────────────────────────────────────

    async def log_agent_activity(self, activity_data: dict) -> Optional[dict]:
        """Log an agent activity event."""
        try:
            result = self._client.table("agent_activities").insert(activity_data).execute()
            return result.data[0]
        except Exception as e:
            if self._client is not None:
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
            if self._client is not None:
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
            if self._client is not None:
                logger.error("Failed to update activity", activity_id=activity_id, error=str(e))
            return None

    # ── Workflow States ──────────────────────────────────────────

    async def save_workflow_state(self, state_data: dict) -> Optional[dict]:
        """Save or update a workflow state."""
        try:
            result = self._client.table("workflow_states").upsert(state_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            if self._client is not None:
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
            if self._client is not None:
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
            if self._client is not None:
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
            if self._client is not None:
                logger.error("Failed to get reports", idea_id=idea_id, error=str(e))
            return []

    async def get_report(self, report_id: str) -> Optional[dict]:
        """Get a specific report."""
        try:
            result = self._client.table("reports").select("*").eq("id", report_id).single().execute()
            return result.data
        except Exception as e:
            if self._client is not None:
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
            if self._client is not None:
                logger.error("Failed to create simulation", error=str(e))
            return None

    async def get_simulation(self, sim_id: str) -> Optional[dict]:
        """Get a simulation by ID."""
        try:
            result = self._client.table("simulations").select("*").eq("id", sim_id).single().execute()
            return result.data
        except Exception as e:
            if self._client is not None:
                logger.error("Failed to get simulation", sim_id=sim_id, error=str(e))
            return None

    async def update_simulation(self, sim_id: str, data: dict) -> Optional[dict]:
        """Update a simulation record."""
        try:
            result = self._client.table("simulations").update(data).eq("id", sim_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            if self._client is not None:
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
            if self._client is not None:
                logger.error("Failed to get simulations", idea_id=idea_id, error=str(e))
            return []


_db_service: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    """Get or create the global database service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
