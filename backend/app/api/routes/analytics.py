"""
Analytics API Routes — usage tracking, credit balance, and cost reporting.
"""

import structlog
from fastapi import APIRouter

logger = structlog.get_logger()
router = APIRouter()


@router.get("/usage")
async def get_usage_summary(user_id: str = "demo-user", days: int = 30):
    """Get usage analytics summary for the dashboard."""
    from app.services.analytics import get_analytics_service
    analytics = get_analytics_service()

    try:
        summary = await analytics.get_usage_summary(user_id, days)
        return summary
    except Exception:
        return {
            "total_events": 0,
            "total_tokens": 0,
            "total_cost_usd": 0,
            "events_by_type": {},
            "daily_usage": [],
            "period_days": days,
        }


@router.get("/credits")
async def get_credits(user_id: str = "demo-user"):
    """Get current credit balance."""
    from app.services.analytics import get_analytics_service
    analytics = get_analytics_service()
    credits = await analytics.get_user_credits(user_id)
    return {"credits": credits, "user_id": user_id}


@router.get("/credits/check")
async def check_credits(event_type: str, user_id: str = "demo-user"):
    """Check if user has enough credits for an operation."""
    from app.services.analytics import get_analytics_service, CREDIT_COSTS
    analytics = get_analytics_service()
    has_credits = await analytics.check_credits(user_id, event_type)
    return {
        "has_credits": has_credits,
        "required": CREDIT_COSTS.get(event_type, 0),
        "event_type": event_type,
    }
