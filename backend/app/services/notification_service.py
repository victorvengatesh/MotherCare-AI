"""Notification service for MotherCare AI — Phase 4 upgrade.

Creates, retrieves and marks in-app notifications.
Phase 4: After persisting to DB, publishes to Redis pub/sub so connected
         WebSocket clients receive the notification in real time.

Notification messages must NOT contain sensitive medical details.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.db import models

logger = logging.getLogger(__name__)


# ─── Allowed notification types ───────────────────────────────────────────────
NOTIF_TYPES = {
    "instruction",
    "appointment_confirmed",
    "appointment_rescheduled",
    "appointment_cancelled",
    "appointment_reminder",
    "reminder",
    "alert_review",
    "follow_up",
}


# ─── Redis publisher (optional) ───────────────────────────────────────────────

def _publish_to_redis(user_id: str, notif: models.Notification):
    """
    Publish notification to Redis channel 'notifications:{user_id}'.
    No-ops silently if Redis is unavailable or not configured.
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return

    try:
        import redis
        r = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
        payload = json.dumps({
            "type": "notification",
            "data": {
                "id": notif.id,
                "notif_type": notif.notif_type,
                "message": notif.message,
                "is_read": False,
                "related_id": notif.related_id,
                "related_type": notif.related_type,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
            },
        }, default=str)
        channel = f"notifications:{user_id}"
        r.publish(channel, payload)
        logger.debug("Published notification to Redis channel %s", channel)
    except Exception as e:
        logger.debug("Redis publish skipped (unavailable): %s", e)


# ─── Public API ───────────────────────────────────────────────────────────────

def create_notification(
    db: Session,
    user_id: str,
    notif_type: str,
    message: str,
    related_id: Optional[str] = None,
    related_type: Optional[str] = None,
    expiry_date: Optional[datetime] = None,
) -> models.Notification:
    """Persist a new notification and push it to WebSocket via Redis."""
    if notif_type not in NOTIF_TYPES:
        notif_type = "follow_up"  # safe default

    notif = models.Notification(
        user_id=user_id,
        notif_type=notif_type,
        message=message,
        is_read=False,
        related_id=related_id,
        related_type=related_type,
        expiry_date=expiry_date,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Phase 4: Push real-time update to WebSocket client via Redis pub/sub
    _publish_to_redis(user_id, notif)

    return notif


def get_notifications(
    db: Session,
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
) -> list[models.Notification]:
    """Return notifications for a given user, newest first."""
    now = datetime.utcnow()
    q = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == user_id,
            (models.Notification.expiry_date == None)
            | (models.Notification.expiry_date > now),
        )
    )
    if unread_only:
        return (
            q.filter(models.Notification.is_read == False)   # noqa: E712
            .order_by(models.Notification.created_at.desc())
            .limit(limit)
            .all()
        )

    return q.order_by(models.Notification.created_at.desc()).limit(limit).all()


def mark_notification_read(db: Session, notif_id: str, user_id: str) -> bool:
    """Mark a single notification as read. Returns False if not found / not owned."""
    notif = (
        db.query(models.Notification)
        .filter_by(id=notif_id, user_id=user_id)
        .first()
    )
    if not notif:
        return False
    notif.is_read = True
    db.commit()
    return True


def mark_all_read(db: Session, user_id: str) -> int:
    """Mark all unread notifications for a user as read. Returns count updated."""
    updated = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == user_id,
            models.Notification.is_read == False,  # noqa: E712
        )
        .all()
    )
    for n in updated:
        n.is_read = True
    db.commit()
    return len(updated)


def _bool_val(v) -> bool:
    """Normalize boolean field — kept for any legacy callers."""
    if isinstance(v, str):
        return v.lower() in ("true", "1")
    return bool(v)
