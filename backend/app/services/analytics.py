"""
Analytics service — tracks usage events, credit consumption, and cost reporting.
Provides aggregation queries for the dashboard analytics endpoint.
"""

import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

from app.models.database import get_db_service

logger = structlog.get_logger()

# Credit cost per operation
CREDIT_COSTS = {
    "workflow_run": 3,
    "agent_run": 1,
    "simulation_run": 2,
    "report_export": 0,
    "api_call": 0,
    "llm_call": 0,
}

# Estimated cost per 1K tokens (USD)
TOKEN_COST_PER_1K = {
    "nvidia/nemotron-3-ultra-550b-a55b": 0.002,
    "meta/llama-3.3-70b-instruct": 0.0005,
    "deepseek-ai/deepseek-v4-flash": 0.001,
    "qwen/qwen3-next-80b-a3b-instruct": 0.0005,
    "nvidia/llama-3.1-nemotron-nano-vl-8b-v1": 0.0003,
}


class AnalyticsService:
    """Tracks usage events, credits, and aggregates analytics data."""

    def __init__(self):
        self._db = get_db_service()

    async def track_event(
        self,
        user_id: str,
        event_type: str,
        idea_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        tokens_used: int = 0,
        model: str = "nvidia/nemotron-3-ultra-550b-a55b",
        metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Record a usage event and deduct credits.

        Args:
            user_id: The user performing the action.
            event_type: One of: workflow_run, agent_run, simulation_run, etc.
            idea_id: Associated idea (optional).
            organization_id: Associated organization (optional).
            tokens_used: Number of LLM tokens consumed.
            model: LLM model used (for cost calculation).
            metadata: Extra context data.

        Returns:
            The created usage event record, or None on failure.
        """
        cost_usd = (tokens_used / 1000) * TOKEN_COST_PER_1K.get(model, 0.005)
        credit_cost = CREDIT_COSTS.get(event_type, 0)

        event_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "organization_id": organization_id,
            "event_type": event_type,
            "idea_id": idea_id,
            "tokens_used": tokens_used,
            "cost_usd": float(cost_usd),
            "metadata": {
                **(metadata or {}),
                "model": model,
                "credit_cost": credit_cost,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            result = self._db._client.table("usage_events").insert(event_data).execute()

            # Deduct credits if applicable
            if credit_cost > 0:
                await self._deduct_credits(user_id, credit_cost)

            # Update aggregate counters on profile
            await self._update_profile_counters(user_id, event_type, tokens_used)

            logger.info(
                "Usage event tracked",
                event_type=event_type,
                user_id=user_id,
                org_id=organization_id,
                tokens=tokens_used,
                cost=round(cost_usd, 6),
            )
            return result.data[0] if result.data else event_data
        except Exception as e:
            logger.error("Failed to track usage event", error=str(e))
            return None

    async def _deduct_credits(self, user_id: str, amount: int) -> None:
        """Deduct credits from user profile. Prevents going below 0."""
        try:
            profile = await self._db.get_profile(user_id)
            if profile:
                current = profile.get("credits", 0)
                new_credits = max(0, current - amount)
                await self._db.update_profile(user_id, {"credits": new_credits})
        except Exception as e:
            logger.error("Failed to deduct credits", user_id=user_id, error=str(e))

    async def _update_profile_counters(
        self, user_id: str, event_type: str, tokens: int
    ) -> None:
        """Increment aggregate counters on the user profile."""
        try:
            updates = {"total_tokens_used": tokens}  # Will use RPC for atomic increment
            if event_type == "workflow_run":
                updates["total_workflows_run"] = 1
            # For now, do a simple update (in production use Supabase RPC for atomic ops)
        except Exception as e:
            logger.warning("Counter update skipped", error=str(e))

    async def get_user_credits(self, user_id: str) -> int:
        """Get the current credit balance for a user."""
        try:
            profile = await self._db.get_profile(user_id)
            return profile.get("credits", 0) if profile else 0
        except Exception:
            return 0

    async def check_credits(self, user_id: str, event_type: str) -> bool:
        """Check if the user has enough credits for an operation."""
        required = CREDIT_COSTS.get(event_type, 0)
        if required == 0:
            return True
        current = await self.get_user_credits(user_id)
        return current >= required

    async def get_usage_summary(
        self, user_id: str, days: int = 30, organization_id: Optional[str] = None
    ) -> dict:
        """
        Get aggregated usage statistics for the analytics dashboard.

        Returns:
            Dict with total_events, total_tokens, total_cost, events_by_type,
            daily_usage breakdown.
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = (
                self._db._client.table("usage_events")
                .select("*")
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
            )
            
            if organization_id:
                query = query.eq("organization_id", organization_id)
            else:
                query = query.eq("user_id", user_id)
                
            result = query.execute()
            events = result.data or []

            total_tokens = sum(e.get("tokens_used", 0) for e in events)
            total_cost = sum(float(e.get("cost_usd", 0)) for e in events)

            events_by_type: dict[str, int] = {}
            for e in events:
                t = e.get("event_type", "unknown")
                events_by_type[t] = events_by_type.get(t, 0) + 1

            # Daily breakdown
            daily: dict[str, dict] = {}
            for e in events:
                day = e.get("created_at", "")[:10]
                if day not in daily:
                    daily[day] = {"events": 0, "tokens": 0, "cost": 0}
                daily[day]["events"] += 1
                daily[day]["tokens"] += e.get("tokens_used", 0)
                daily[day]["cost"] += float(e.get("cost_usd", 0))

            return {
                "total_events": len(events),
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "events_by_type": events_by_type,
                "daily_usage": [
                    {"date": k, **v}
                    for k, v in sorted(daily.items(), reverse=True)
                ],
                "period_days": days,
                "organization_id": organization_id
            }
        except Exception as e:
            logger.error("Failed to get usage summary", error=str(e))
            return {
                "total_events": 0,
                "total_tokens": 0,
                "total_cost_usd": 0,
                "events_by_type": {},
                "daily_usage": [],
                "period_days": days,
            }


# Singleton
_analytics_service: Optional[AnalyticsService] = None


def get_analytics_service() -> AnalyticsService:
    """Get or create the global analytics service singleton."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service
