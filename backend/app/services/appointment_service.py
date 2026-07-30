"""Appointment service for MotherCare AI.

Handles:
- Appointment creation with past-date and schedule-conflict guards
- Status transition enforcement
- Audit trail logging
- Notification dispatch on status changes
- Phase 4: Email notifications on status changes
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.db import models
from app.services.alert_service import create_audit_event
from app.services.notification_service import create_notification
from app.utils.logger import logger

# ─── Valid status transitions ─────────────────────────────────────────────────
VALID_TRANSITIONS = {
    "requested":    {"confirmed", "cancelled"},
    "confirmed":    {"rescheduled", "completed", "no_show", "cancelled"},
    "rescheduled":  {"confirmed", "cancelled"},
    "completed":    set(),   # terminal
    "cancelled":    set(),   # terminal
    "no_show":      set(),   # terminal
}

APPOINTMENT_TYPES = {"checkup", "emergency", "follow_up", "scan", "consultation", "other"}


def assert_doctor_patient_access(db: Session, doctor: models.User, patient_id: str):
    """Raise 403 if the doctor is not assigned to this patient (unless admin)."""
    if doctor.role == "admin":
        return
    assignment = (
        db.query(models.DoctorPatientAssignment)
        .filter(
            models.DoctorPatientAssignment.doctor_id == doctor.id,
            models.DoctorPatientAssignment.patient_id == patient_id,
            models.DoctorPatientAssignment.status == "active",
        )
        .first()
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not assigned to this patient.",
        )


def check_schedule_conflict(
    db: Session,
    doctor_id: str,
    appointment_datetime: datetime,
    buffer_minutes: int = 30,
    exclude_id: Optional[str] = None,
) -> bool:
    """Return True if there is a scheduling conflict within ±buffer_minutes."""
    window_start = appointment_datetime - timedelta(minutes=buffer_minutes)
    window_end   = appointment_datetime + timedelta(minutes=buffer_minutes)

    q = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.status.in_(["requested", "confirmed", "rescheduled"]),
        models.Appointment.appointment_datetime >= window_start,
        models.Appointment.appointment_datetime <= window_end,
    )
    if exclude_id:
        q = q.filter(models.Appointment.id != exclude_id)

    return q.first() is not None


def create_appointment(
    db: Session,
    patient_id: str,
    doctor_id: str,
    appointment_datetime: datetime,
    appointment_type: str,
    reason: str,
    created_by: models.User,
) -> models.Appointment:
    """Create a new appointment with validation."""
    # Past-date guard
    if appointment_datetime <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Appointment date and time must be in the future.",
        )

    # Type validation
    if appointment_type not in APPOINTMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid appointment type. Must be one of: {', '.join(sorted(APPOINTMENT_TYPES))}",
        )

    # Schedule conflict check
    if check_schedule_conflict(db, doctor_id, appointment_datetime):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor has a conflicting appointment within 30 minutes of the requested time.",
        )

    appt = models.Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_datetime=appointment_datetime,
        appointment_type=appointment_type,
        reason=reason,
        status="requested",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    create_audit_event(db, actor_id=created_by.id, action="appointment_created", target_id=appt.id)

    # Notify patient
    create_notification(
        db,
        user_id=patient_id,
        notif_type="appointment_confirmed",
        message=f"Your appointment request ({appointment_type}) has been received.",
        related_id=appt.id,
        related_type="appointment",
    )

    logger.info("Appointment created: %s patient=%s", appt.id, patient_id)
    return appt


def update_appointment_status(
    db: Session,
    appt: models.Appointment,
    new_status: str,
    actor: models.User,
    reason: Optional[str] = None,
    doctor_notes: Optional[str] = None,
    patient_instructions: Optional[str] = None,
    new_datetime: Optional[datetime] = None,
) -> models.Appointment:
    """Apply a status transition with enforcement and audit logging."""
    current = appt.status
    allowed = VALID_TRANSITIONS.get(current, set())

    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot transition appointment from '{current}' to '{new_status}'. Allowed: {sorted(allowed) or 'none (terminal)'}",
        )

    # Require reason for cancellation / rescheduling
    if new_status in ("cancelled", "rescheduled") and not reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A reason is required when {new_status}.",
        )

    if new_status == "rescheduled" and new_datetime:
        if new_datetime <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Rescheduled appointment must be in the future.",
            )
        # Conflict check (excluding this appointment)
        if check_schedule_conflict(db, appt.doctor_id, new_datetime, exclude_id=appt.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Doctor has a conflicting appointment within 30 minutes of the rescheduled time.",
            )
        appt.appointment_datetime = new_datetime
        appt.reschedule_reason = reason
    elif new_status == "cancelled":
        appt.cancellation_reason = reason

    appt.status = new_status
    if doctor_notes is not None:
        appt.doctor_notes = doctor_notes
    if patient_instructions is not None:
        appt.patient_instructions = patient_instructions

    db.commit()
    db.refresh(appt)

    create_audit_event(
        db, actor_id=actor.id,
        action=f"appointment_{new_status}",
        target_id=appt.id,
        meta={"reason": reason or ""},
    )

    # Notify patient (in-app)
    msg_map = {
        "confirmed":   "Your appointment has been confirmed by your doctor.",
        "rescheduled": "Your appointment has been rescheduled. Please check your appointments.",
        "cancelled":   "Your appointment has been cancelled.",
        "completed":   "Your appointment has been marked as completed.",
        "no_show":     "You were marked as no-show for your appointment.",
    }
    if new_status in msg_map:
        nt = f"appointment_{new_status}" if f"appointment_{new_status}" in {
            "appointment_confirmed", "appointment_rescheduled", "appointment_cancelled"
        } else "appointment_reminder"
        try:
            create_notification(
                db,
                user_id=appt.patient_id,
                notif_type=nt,
                message=msg_map[new_status],
                related_id=appt.id,
                related_type="appointment",
            )
        except Exception as e:
            logger.warning("Failed to create appointment notification: %s", e)

    # Phase 4: Email patient on key status changes
    try:
        patient = db.query(models.User).filter_by(id=appt.patient_id).first()
        doctor  = db.query(models.User).filter_by(id=appt.doctor_id).first()
        if patient and doctor:
            from app.services.email_service import (
                send_appointment_confirmation,
                send_appointment_rescheduled,
                send_appointment_cancelled,
            )
            from app.utils.tasks import run_in_background
            
            appt_dt = appt.appointment_datetime.strftime("%Y-%m-%d %H:%M UTC")
            if new_status == "confirmed":
                run_in_background(send_appointment_confirmation(
                    patient_email=patient.email,
                    patient_name=patient.username,
                    doctor_name=doctor.username,
                    appointment_datetime=appt_dt,
                    appointment_type=appt.appointment_type,
                    reason=appt.reason,
                ))
            elif new_status == "rescheduled":
                run_in_background(send_appointment_rescheduled(
                    patient_email=patient.email,
                    patient_name=patient.username,
                    doctor_name=doctor.username,
                    new_datetime=appt_dt,
                    reschedule_reason=reason or "",
                ))
            elif new_status == "cancelled":
                run_in_background(send_appointment_cancelled(
                    patient_email=patient.email,
                    patient_name=patient.username,
                    doctor_name=doctor.username,
                    cancellation_reason=reason or "",
                ))
    except Exception as e:
        logger.debug("Appointment email skipped: %s", e)

    return appt


def serialize_appointment(appt: models.Appointment, include_private: bool = False) -> dict:
    """Return a safe dict representation of an appointment."""
    d = {
        "id": appt.id,
        "patient_id": appt.patient_id,
        "doctor_id": appt.doctor_id,
        "appointment_datetime": appt.appointment_datetime.isoformat(),
        "appointment_type": appt.appointment_type,
        "reason": appt.reason,
        "status": appt.status,
        "patient_instructions": appt.patient_instructions,
        "created_at": appt.created_at.isoformat(),
        "updated_at": appt.updated_at.isoformat() if appt.updated_at else None,
    }
    if include_private:
        d["doctor_notes"] = appt.doctor_notes
        d["reschedule_reason"] = appt.reschedule_reason
        d["cancellation_reason"] = appt.cancellation_reason
    return d
