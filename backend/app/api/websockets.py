"""
WebSocket endpoints for real-time agent activity and simulation streaming.
"""

import structlog
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

logger = structlog.get_logger()
router = APIRouter()

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
async def agent_activity_stream(websocket: WebSocket, idea_id: str):
    """WebSocket endpoint for streaming agent activity in real-time."""
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
async def simulation_stream(websocket: WebSocket, sim_id: str):
    """WebSocket endpoint for streaming simulation dialogue."""
    await manager.connect(sim_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Received simulation WS message", sim_id=sim_id, data=data)
    except WebSocketDisconnect:
        manager.disconnect(sim_id, websocket)
