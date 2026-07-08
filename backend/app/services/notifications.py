import structlog
import httpx
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models.database import get_db_connection, _serialize_json

logger = structlog.get_logger()


class NotificationService:
    """In-app notification management and webhook dispatch."""

    def __init__(self):
        pass

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
            data = _serialize_json(notif)
            keys = list(data.keys())
            values = list(data.values())
            placeholders = ", ".join(["?"] * len(keys))
            query = f"INSERT INTO notifications ({', '.join(keys)}) VALUES ({placeholders})"
            async with get_db_connection() as conn:
                await conn.execute(query, values)
                await conn.commit()
            logger.info("Notification created", user_id=user_id, type=notification_type)
            return notif
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
            query = "SELECT * FROM notifications WHERE user_id = ?"
            params = [user_id]
            if unread_only:
                query += " AND is_read = 0"
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            async with get_db_connection() as conn:
                async with conn.execute(query, params) as cursor:
                    results = await cursor.fetchall()
                    for r in results:
                        r['is_read'] = bool(r['is_read'])
                    return results
        except Exception as e:
            logger.error("Failed to get notifications", error=str(e))
            return []

    async def get_unread_count(self, user_id: str) -> int:
        """Get the count of unread notifications."""
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT COUNT(id) as c FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)) as cursor:
                    res = await cursor.fetchone()
                    return res["c"] if res else 0
        except Exception as e:
            logger.error("Failed to get unread count", error=str(e))
            return 0

    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a single notification as read."""
        try:
            async with get_db_connection() as conn:
                await conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, user_id))
                await conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to mark notification read", error=str(e))
            return False

    async def mark_all_read(self, user_id: str) -> bool:
        """Mark all unread notifications as read for a user."""
        try:
            async with get_db_connection() as conn:
                await conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0", (user_id,))
                await conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to mark all read", error=str(e))
            return False

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification."""
        try:
            async with get_db_connection() as conn:
                await conn.execute("DELETE FROM notifications WHERE id = ? AND user_id = ?", (notification_id, user_id))
                await conn.commit()
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
            webhook_url = None
            async with get_db_connection() as conn:
                async with conn.execute("SELECT webhook_url FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
                    res = await cursor.fetchone()
                    webhook_url = res["webhook_url"] if res else None

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
