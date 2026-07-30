"""
WebSocket Connection Manager for MotherCare AI — Phase 4

Manages active WebSocket connections keyed by user_id.
Supports broadcasting messages to individual users (multi-tab safe).
"""

import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Thread-safe manager for active WebSocket connections.

    - Multiple connections per user are supported (multi-tab).
    - Disconnected sockets are silently removed on next send attempt.
    """

    def __init__(self):
        # user_id → set of active WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._connections[user_id].add(websocket)
        logger.info("WS connected: user=%s  total_conns=%d", user_id, self.total_connections)

    def disconnect(self, user_id: str, websocket: WebSocket):
        """Remove a WebSocket from the registry."""
        self._connections[user_id].discard(websocket)
        if not self._connections[user_id]:
            del self._connections[user_id]
        logger.info("WS disconnected: user=%s  total_conns=%d", user_id, self.total_connections)

    async def send_to_user(self, user_id: str, data: dict):
        """
        Send a JSON message to all active connections for a user.
        Silently removes broken connections.
        """
        if user_id not in self._connections:
            return

        dead: Set[WebSocket] = set()
        payload = json.dumps(data, default=str)

        for ws in list(self._connections[user_id]):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)

        for ws in dead:
            self._connections[user_id].discard(ws)

        if dead:
            logger.debug("Removed %d dead WS connections for user=%s", len(dead), user_id)

    async def broadcast(self, data: dict):
        """Broadcast a message to ALL connected users (use sparingly)."""
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, data)

    @property
    def total_connections(self) -> int:
        return sum(len(v) for v in self._connections.values())

    @property
    def connected_users(self) -> list:
        return list(self._connections.keys())


# ---------------------------------------------------------------------------
# Singleton instance shared across the application
# ---------------------------------------------------------------------------
manager = ConnectionManager()
