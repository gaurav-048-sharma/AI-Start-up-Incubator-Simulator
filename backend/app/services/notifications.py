"""
Notification service — manages in-app notifications and webhook dispatch.
Supports workflow completion alerts, credit warnings, and custom webhooks.
"""

import structlog
import httpx
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models.database import get_db_service

logger = structlog.get_logger()


class NotificationService:
    """In-app notification management and webhook dispatch."""

    def __init__(self):
        self._db = get_db_service()

    async def create(
        self,
        user_id: str,
        title: str,
        body: str = "",
        notification_type: str = "info",
        action_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """Create an in-app notification for a user."""
        notif = {
            "id": str(uuid4()),
            "user_id": user_id,
            "title": title,
            "body": body,
            "notification_type": notification_type,
            "is_read": False,
            "action_url": action_url,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            result = self._db._client.table("notifications").insert(notif).execute()
            logger.info("Notification created", user_id=user_id, type=notification_type)
            return result.data[0] if result.data else notif
        except Exception as e:
            logger.error("Failed to create notification", error=str(e))
            return None

    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        """Get notifications for a user, optionally filtered to unread only."""
        try:
            query = (
                self._db._client.table("notifications")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
            )
            if unread_only:
                query = query.eq("is_read", False)

            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error("Failed to get notifications", error=str(e))
            return []

    async def get_unread_count(self, user_id: str) -> int:
        """Get the count of unread notifications."""
        try:
            result = (
                self._db._client.table("notifications")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("is_read", False)
                .execute()
            )
            return result.count or 0
        except Exception as e:
            logger.error("Failed to get unread count", error=str(e))
            return 0

    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a single notification as read."""
        try:
            self._db._client.table("notifications").update(
                {"is_read": True}
            ).eq("id", notification_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            logger.error("Failed to mark notification read", error=str(e))
            return False

    async def mark_all_read(self, user_id: str) -> bool:
        """Mark all notifications as read for a user."""
        try:
            self._db._client.table("notifications").update(
                {"is_read": True}
            ).eq("user_id", user_id).eq("is_read", False).execute()
            return True
        except Exception as e:
            logger.error("Failed to mark all read", error=str(e))
            return False

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a specific notification."""
        try:
            self._db._client.table("notifications").delete().eq(
                "id", notification_id
            ).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            logger.error("Failed to delete notification", error=str(e))
            return False

    # ── Workflow event notifications ─────────────────────────────

    async def notify_workflow_complete(
        self, user_id: str, idea_id: str, idea_title: str, status: str
    ) -> None:
        """Send notification when an incubation workflow completes."""
        if status == "completed":
            await self.create(
                user_id=user_id,
                title="Incubation Complete! 🎉",
                body=f'Your idea "{idea_title}" has finished the full incubation pipeline. View your reports now.',
                notification_type="workflow_complete",
                action_url=f"/dashboard/ideas/{idea_id}",
                metadata={"idea_id": idea_id, "status": status},
            )
        elif status == "failed":
            await self.create(
                user_id=user_id,
                title="Workflow Failed ⚠️",
                body=f'The incubation workflow for "{idea_title}" encountered an error. You can retry from the idea page.',
                notification_type="error",
                action_url=f"/dashboard/ideas/{idea_id}",
                metadata={"idea_id": idea_id, "status": status},
            )

        # Dispatch webhook if configured
        await self._dispatch_webhook(user_id, {
            "event": "workflow_complete",
            "idea_id": idea_id,
            "idea_title": idea_title,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def notify_simulation_complete(
        self, user_id: str, idea_id: str, idea_title: str, outcome: str
    ) -> None:
        """Send notification when a pitch simulation completes."""
        outcome_label = {"funded": "Funded! 💰", "conditional": "Conditional 🤔", "passed": "Passed 📋"}
        await self.create(
            user_id=user_id,
            title=f"Pitch Result: {outcome_label.get(outcome, outcome)}",
            body=f'Investor simulation for "{idea_title}" is complete. See the full transcript and feedback.',
            notification_type="simulation_complete",
            action_url=f"/dashboard/simulation",
            metadata={"idea_id": idea_id, "outcome": outcome},
        )

    async def notify_credits_low(self, user_id: str, remaining: int) -> None:
        """Warn user when credits are running low."""
        if remaining <= 3:
            await self.create(
                user_id=user_id,
                title=f"Credits Low ({remaining} remaining)",
                body="You're running low on credits. Upgrade your plan to continue using AI features.",
                notification_type="credit_low",
                action_url="/dashboard/settings",
                metadata={"credits_remaining": remaining},
            )

    # ── Webhook dispatch ─────────────────────────────────────────

    async def _dispatch_webhook(self, user_id: str, payload: dict) -> None:
        """Send a webhook POST to the user's configured URL, if any."""
        try:
            settings = (
                self._db._client.table("user_settings")
                .select("webhook_url")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            webhook_url = settings.data.get("webhook_url") if settings.data else None

            if not webhook_url:
                return

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json", "X-Source": "ai-incubator"},
                )
                logger.info("Webhook dispatched", url=webhook_url, status=resp.status_code)
        except Exception as e:
            logger.warning("Webhook dispatch failed", user_id=user_id, error=str(e))


# Singleton
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the global notification service singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
