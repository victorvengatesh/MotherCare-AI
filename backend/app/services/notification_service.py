"""Notification service for MotherCare AI.

Creates, retrieves and marks in-app notifications.
Notification messages must NOT contain sensitive medical details.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.db import models


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


def create_notification(
    db: Session,
    user_id: str,
    notif_type: str,
    message: str,
    related_id: Optional[str] = None,
    related_type: Optional[str] = None,
    expiry_date: Optional[datetime] = None,
) -> models.Notification:
    """Persist a new notification. message must be non-sensitive."""
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
        # Python-level check for unread because SQLite JSON booleans
        notifs = q.order_by(models.Notification.created_at.desc()).all()
        return [n for n in notifs if not _bool_val(n.is_read)][:limit]

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
    notifs = get_notifications(db, user_id, unread_only=True)
    for n in notifs:
        n.is_read = True
    db.commit()
    return len(notifs)


def _bool_val(v) -> bool:
    """Normalize SQLite JSON boolean field."""
    if isinstance(v, str):
        return v.lower() in ("true", "1")
    return bool(v)
