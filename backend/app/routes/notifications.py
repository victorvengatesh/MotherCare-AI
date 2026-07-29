"""In-app notification API routes for MotherCare AI."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.services.notification_service import (
    get_notifications, mark_notification_read, mark_all_read, _bool_val,
)
from app.schemas.response import StandardResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _serialize_notif(n: models.Notification) -> dict:
    return {
        "id": n.id,
        "type": n.notif_type,
        "message": n.message,
        "is_read": _bool_val(n.is_read),
        "related_id": n.related_id,
        "related_type": n.related_type,
        "created_at": n.created_at.isoformat(),
        "expiry_date": n.expiry_date.isoformat() if n.expiry_date else None,
    }


@router.get("", response_model=StandardResponse[dict])
async def list_notifications(
    unread_only: bool = Query(False),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return notifications for the current user."""
    notifs = get_notifications(db, current_user.id, unread_only=unread_only)
    unread_count = sum(1 for n in notifs if not _bool_val(n.is_read))
    return StandardResponse(
        status="success",
        data={
            "notifications": [_serialize_notif(n) for n in notifs],
            "unread_count": unread_count,
        },
    )


@router.post("/{notif_id}/read", response_model=StandardResponse[dict])
async def mark_read(
    notif_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    success = mark_notification_read(db, notif_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found or does not belong to you.")
    return StandardResponse(status="success", message="Notification marked as read.")


@router.post("/read-all", response_model=StandardResponse[dict])
async def mark_all_read_endpoint(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all unread notifications as read."""
    count = mark_all_read(db, current_user.id)
    return StandardResponse(status="success", message=f"{count} notifications marked as read.")
