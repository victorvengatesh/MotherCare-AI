"""
WebSocket Routes for MotherCare AI — Phase 4

Endpoint:
  GET /ws/notifications?token=<JWT>

Delivers real-time notifications to authenticated users via WebSocket.
Falls back gracefully when Redis pub/sub is unavailable.
"""

import asyncio
import json
import logging
import os

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from app.core.connection_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Heartbeat interval in seconds — keeps connections alive through proxies/firewalls
HEARTBEAT_INTERVAL = 30


def _decode_ws_token(token: str) -> dict | None:
    """Decode and validate a JWT token for WebSocket auth. Returns payload or None."""
    from app.services.auth_service import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type", "access") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None


async def _redis_subscriber(user_id: str, websocket: WebSocket):
    """
    Subscribe to Redis pub/sub channel notifications:{user_id} and forward
    messages to the WebSocket.  No-ops gracefully if Redis is unavailable.
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return  # Redis not configured — polling mode only

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, decode_responses=True)
        pubsub = r.pubsub()
        channel = f"notifications:{user_id}"
        await pubsub.subscribe(channel)
        logger.info("WS: Subscribed to Redis channel %s", channel)

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await manager.send_to_user(user_id, data)
                except Exception as e:
                    logger.debug("WS Redis message parse error: %s", e)

    except Exception as e:
        logger.warning("WS Redis subscriber error for user=%s: %s", user_id, e)
    finally:
        try:
            await pubsub.unsubscribe()
            await r.aclose()
        except Exception:
            pass


async def _client_receive_loop(websocket: WebSocket):
    """Keep connection alive and listen for client disconnects/heartbeats."""
    while True:
        try:
            # Wait for client message (client is read-only, but we must read to detect disconnects)
            await asyncio.wait_for(
                websocket.receive_text(),
                timeout=HEARTBEAT_INTERVAL,
            )
        except asyncio.TimeoutError:
            # Send heartbeat ping
            await websocket.send_json({"type": "ping"})


@router.websocket("/notifications")
async def ws_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    Real-time notification stream.

    Connect: ws://host/ws/notifications?token=<JWT>
    Protocol:
      Server → Client: {"type": "notification", "data": {...}}
      Server → Client: {"type": "ping"}  (heartbeat every 30s)
      Client → Server: any text (ignored — connection is read-only)
    """
    # ── Authenticate ──────────────────────────────────────────────────────
    payload = _decode_ws_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id: str = payload.get("sub")
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # ── Register connection ───────────────────────────────────────────────
    await manager.connect(user_id, websocket)

    # ── Start concurrent loops ───────────────────────────────────────────
    receive_task = asyncio.create_task(_client_receive_loop(websocket))
    redis_task = asyncio.create_task(_redis_subscriber(user_id, websocket))

    try:
        # Wait until either the client disconnects or the Redis subscriber exits
        done, pending = await asyncio.wait(
            [receive_task, redis_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            exc = task.exception()
            if exc:
                raise exc

    except WebSocketDisconnect:
        logger.info("WS client disconnected: user=%s", user_id)
    except Exception as e:
        logger.warning("WS error for user=%s: %s", user_id, e)
    finally:
        receive_task.cancel()
        redis_task.cancel()
        # Clean up tasks cleanly
        await asyncio.gather(receive_task, redis_task, return_exceptions=True)
        manager.disconnect(user_id, websocket)

