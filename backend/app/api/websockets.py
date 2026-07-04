"""
WebSocket endpoints for real-time agent activity and simulation streaming.
Now includes JWT authentication via query parameter.
"""

import structlog
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime, timezone

logger = structlog.get_logger()
router = APIRouter()


async def _authenticate_ws(websocket: WebSocket, token: str | None) -> dict | None:
    """
    Validate a JWT token for WebSocket connections.
    Returns the user dict on success, or None on failure.
    WebSocket cannot use standard HTTP auth headers, so we accept the token
    as a query parameter: ws://host/ws/...?token=<jwt>
    """
    if not token:
        return None

    try:
        from app.config import get_settings
        settings = get_settings()

        if not settings.has_supabase:
            # Demo mode — allow all connections
            return {"id": "demo-user", "org_id": "demo-org", "platform_role": "user"}

        import asyncio as _asyncio
        from app.models.database import get_supabase_client
        supabase = get_supabase_client(admin=True)
        if not supabase:
            return None

        user_response = await _asyncio.to_thread(supabase.auth.get_user, token)
        if not user_response or not user_response.user:
            return None

        user = user_response.user
        user_id = str(user.id)

        # Fetch platform role
        profile = await _asyncio.to_thread(
            lambda: supabase.table("profiles")
            .select("platform_role")
            .eq("id", user_id)
            .single()
            .execute()
        )
        platform_role = "user"
        if profile.data and isinstance(profile.data, dict):
            platform_role = profile.data.get("platform_role", "user")

        return {
            "id": user_id,
            "email": user.email,
            "platform_role": platform_role,
        }
    except Exception as e:
        logger.warning("WebSocket auth failed", error=str(e))
        return None


async def _verify_idea_access(user: dict, idea_id: str) -> bool:
    """Check if the authenticated user has access to the given idea."""
    if user.get("platform_role") == "super_admin":
        return True

    try:
        import asyncio as _asyncio
        from app.models.database import get_supabase_client
        supabase = get_supabase_client(admin=True)
        if not supabase:
            return False

        idea = await _asyncio.to_thread(
            lambda: supabase.table("ideas")
            .select("user_id, organization_id")
            .eq("id", idea_id)
            .single()
            .execute()
        )
        if not idea.data:
            return False

        # Owner check
        if idea.data.get("user_id") == user["id"]:
            return True

        # Org membership check
        org_id = idea.data.get("organization_id")
        if org_id:
            membership = await _asyncio.to_thread(
                lambda: supabase.table("organization_members")
                .select("role")
                .eq("organization_id", org_id)
                .eq("user_id", user["id"])
                .single()
                .execute()
            )
            if membership.data:
                return True

        return False
    except Exception as e:
        logger.warning("WebSocket idea access check failed", error=str(e))
        return False


# Connection manager for broadcasting events
class ConnectionManager:
    """Manages WebSocket connections for real-time broadcasting."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, idea_id: str, websocket: WebSocket):
        await websocket.accept()
        if idea_id not in self._connections:
            self._connections[idea_id] = []
        self._connections[idea_id].append(websocket)
        logger.info("WebSocket connected", idea_id=idea_id)

    def disconnect(self, idea_id: str, websocket: WebSocket):
        if idea_id in self._connections:
            self._connections[idea_id].remove(websocket)
            if not self._connections[idea_id]:
                del self._connections[idea_id]
        logger.info("WebSocket disconnected", idea_id=idea_id)

    async def broadcast(self, idea_id: str, message: dict):
        if idea_id in self._connections:
            disconnected = []
            for ws in self._connections[idea_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                self.disconnect(idea_id, ws)


manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    return manager


@router.websocket("/ws/ideas/{idea_id}/agents")
async def agent_activity_stream(
    websocket: WebSocket,
    idea_id: str,
    token: str | None = Query(default=None),
):
    """
    WebSocket endpoint for streaming agent activity in real-time.
    Requires JWT authentication via ?token=<jwt> query parameter.
    """
    user = await _authenticate_ws(websocket, token)
    if not user:
        await websocket.close(code=4001, reason="Authentication required")
        return

    has_access = await _verify_idea_access(user, idea_id)
    if not has_access:
        await websocket.close(code=4003, reason="Access denied to this idea")
        return

    await manager.connect(idea_id, websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()
            # Client can send control messages (pause, resume, etc.)
            logger.debug("Received WS message", idea_id=idea_id, data=data)
    except WebSocketDisconnect:
        manager.disconnect(idea_id, websocket)


@router.websocket("/ws/simulations/{sim_id}")
async def simulation_stream(
    websocket: WebSocket,
    sim_id: str,
    token: str | None = Query(default=None),
):
    """
    WebSocket endpoint for streaming simulation dialogue.
    Requires JWT authentication via ?token=<jwt> query parameter.
    """
    user = await _authenticate_ws(websocket, token)
    if not user:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # For simulations, we trust that authenticated users can access their sim
    # (the sim_id is a UUID, not guessable, and the user needed auth to create it)
    await manager.connect(sim_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Received simulation WS message", sim_id=sim_id, data=data)
    except WebSocketDisconnect:
        manager.disconnect(sim_id, websocket)
