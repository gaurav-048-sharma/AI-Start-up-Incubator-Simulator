"""
Notifications API Routes — in-app notification management.
"""

import structlog
from fastapi import APIRouter, Depends
from app.middleware.security import get_current_user
from pydantic import BaseModel
from typing import Optional

logger = structlog.get_logger()
router = APIRouter()

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    body: Optional[str] = None
    notification_type: str = "info"
    is_read: bool = False
    action_url: Optional[str] = None
    metadata: dict = {}
    created_at: Optional[str] = None

@router.get("")
async def get_notifications(
    user: dict = Depends(get_current_user),
    unread_only: bool = False,
    limit: int = 20,
):
    """Get user notifications with optional unread filter."""
    user_id = user["id"]
    from app.services.notifications import get_notification_service
    svc = get_notification_service()
    notifications = await svc.get_user_notifications(user_id, unread_only, limit)
    unread_count = await svc.get_unread_count(user_id)
    return {
        "notifications": notifications,
        "unread_count": unread_count,
        "total": len(notifications),
    }

@router.get("/unread-count")
async def get_unread_count(user: dict = Depends(get_current_user)):
    """Get the count of unread notifications."""
    user_id = user["id"]
    from app.services.notifications import get_notification_service
    svc = get_notification_service()
    count = await svc.get_unread_count(user_id)
    return {"unread_count": count}

@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    """Mark a single notification as read."""
    user_id = user["id"]
    from app.services.notifications import get_notification_service
    svc = get_notification_service()
    success = await svc.mark_read(notification_id, user_id)
    return {"success": success}

@router.post("/mark-all-read")
async def mark_all_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    user_id = user["id"]
    from app.services.notifications import get_notification_service
    svc = get_notification_service()
    success = await svc.mark_all_read(user_id)
    return {"success": success}

@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, user: dict = Depends(get_current_user)):
    """Delete a specific notification."""
    user_id = user["id"]
    from app.services.notifications import get_notification_service
    svc = get_notification_service()
    success = await svc.delete_notification(notification_id, user_id)
    return {"success": success}
