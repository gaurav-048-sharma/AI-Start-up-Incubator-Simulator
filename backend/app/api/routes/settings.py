"""
Settings API Routes — user preference management and persistence.
"""

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

logger = structlog.get_logger()
router = APIRouter()


class UserSettingsUpdate(BaseModel):
    """Request body for updating user settings."""
    llm_provider: Optional[str] = Field(None, description="openai or anthropic")
    llm_model: Optional[str] = Field(None, description="LLM model name")
    max_iterations: Optional[int] = Field(None, ge=1, le=15)
    quality_threshold: Optional[float] = Field(None, ge=0, le=1)
    notification_email: Optional[bool] = None
    notification_in_app: Optional[bool] = None
    webhook_url: Optional[str] = None
    theme: Optional[str] = Field(None, description="dark or light")


class UserSettingsResponse(BaseModel):
    """User settings response."""
    user_id: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    max_iterations: int = 5
    quality_threshold: float = 0.7
    notification_email: bool = True
    notification_in_app: bool = True
    webhook_url: Optional[str] = None
    theme: str = "dark"
    updated_at: Optional[str] = None


@router.get("", response_model=UserSettingsResponse)
async def get_settings(user_id: str = "demo-user"):
    """Get user settings (creates defaults if not exists)."""
    from app.models.database import get_db_service
    db = get_db_service()

    try:
        result = (
            db._client.table("user_settings")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if result.data:
            return result.data
    except Exception:
        pass

    # Return defaults if no saved settings exist
    return UserSettingsResponse(user_id=user_id)


@router.patch("", response_model=UserSettingsResponse)
async def update_settings(update: UserSettingsUpdate, user_id: str = "demo-user"):
    """Update user settings. Creates the record if it doesn't exist."""
    from app.models.database import get_db_service
    db = get_db_service()

    # Validate provider/model combinations
    valid_models = {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "anthropic": ["claude-sonnet-4-20250514", "claude-3-haiku-20240307"],
    }

    update_data = update.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["user_id"] = user_id

    if "llm_provider" in update_data and "llm_model" in update_data:
        provider = update_data["llm_provider"]
        model = update_data["llm_model"]
        if provider in valid_models and model not in valid_models[provider]:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' is not valid for provider '{provider}'. Valid: {valid_models[provider]}",
            )

    try:
        if db._client is None:
            # Mock mode — return merged defaults
            return UserSettingsResponse(user_id=user_id, **{k: v for k, v in update_data.items() if k != "user_id"})
        result = db._client.table("user_settings").upsert(update_data).execute()
        if result.data:
            return result.data[0]
        return UserSettingsResponse(user_id=user_id, **{k: v for k, v in update_data.items() if k != "user_id"})
    except Exception as e:
        logger.error("Failed to update settings", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save settings")
