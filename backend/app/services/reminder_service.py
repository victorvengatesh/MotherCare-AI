"""Medicine reminder service for MotherCare AI.

Safety rules enforced here:
- Only assigned doctors may create doctor-sourced reminders.
- Patients create self_added reminders only for themselves.
- Gemini / AI must never prescribe or modify dosage.
- No cross-patient data leakage.
- Audit trail for every doctor-created change.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db import models
from app.services.alert_service import create_audit_event
from app.services.notification_service import create_notification
from app.utils.logger import logger

# ─── Allowed frequency values (free-text validated against this list) ─────────
ALLOWED_FREQUENCIES = {
    "once daily", "twice daily", "three times daily", "four times daily",
    "every 4 hours", "every 6 hours", "every 8 hours", "every 12 hours",
    "weekly", "as needed", "with meals", "before meals", "after meals",
    "at bedtime",
}

ALLOWED_DOSE_STATUSES = {"taken", "skipped", "missed"}


def _bool_val(v) -> bool:
    if isinstance(v, str):
        return v.lower() in ("true", "1")
    return bool(v)


def _check_doctor_patient_access(db: Session, doctor: models.User, patient_id: str):
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


def create_doctor_reminder(
    db: Session,
    doctor: models.User,
    patient_id: str,
    medicine_name: str,
    dosage: str,
    frequency: str,
    reminder_times: list,
    start_date: datetime,
    end_date: Optional[datetime],
    instructions: Optional[str],
) -> models.MedicineReminder:
    """Doctor creates a prescription reminder for an assigned patient."""
    _check_doctor_patient_access(db, doctor, patient_id)

    if not medicine_name.strip():
        raise HTTPException(status_code=422, detail="medicine_name must not be empty.")

    if not dosage.strip():
        raise HTTPException(status_code=422, detail="dosage must not be empty.")

    freq_lower = frequency.lower().strip()
    if freq_lower not in ALLOWED_FREQUENCIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid frequency. Must be one of: {sorted(ALLOWED_FREQUENCIES)}",
        )

    if start_date < datetime.utcnow() - datetime.resolution * 86400:  # allow today
        pass  # start_date validation is lenient (can start from today)

    if end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date.")

    # Validate reminder times format (HH:MM)
    for t in reminder_times:
        try:
            datetime.strptime(t, "%H:%M")
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid reminder time '{t}'. Use HH:MM format.")

    reminder = models.MedicineReminder(
        patient_id=patient_id,
        prescribed_by=doctor.id,
        medicine_name=medicine_name.strip(),
        dosage=dosage.strip(),
        frequency=freq_lower,
        reminder_times=reminder_times,
        start_date=start_date,
        end_date=end_date,
        instructions=instructions,
        source="doctor",
        is_active=True,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    create_audit_event(
        db, actor_id=doctor.id,
        action="reminder_created",
        target_id=reminder.id,
        meta={"patient_id": patient_id, "medicine": medicine_name},
    )

    create_notification(
        db,
        user_id=patient_id,
        notif_type="reminder",
        message=f"A new medicine reminder has been added by your doctor.",
        related_id=reminder.id,
        related_type="reminder",
    )

    return reminder


def create_self_reminder(
    db: Session,
    patient: models.User,
    medicine_name: str,
    dosage: str,
    frequency: str,
    reminder_times: list,
    start_date: datetime,
    end_date: Optional[datetime],
    instructions: Optional[str],
) -> models.MedicineReminder:
    """Patient creates a personal (self_added) reminder."""
    if not medicine_name.strip():
        raise HTTPException(status_code=422, detail="medicine_name must not be empty.")
    if not dosage.strip():
        raise HTTPException(status_code=422, detail="dosage must not be empty.")

    freq_lower = frequency.lower().strip()
    if freq_lower not in ALLOWED_FREQUENCIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid frequency. Must be one of: {sorted(ALLOWED_FREQUENCIES)}",
        )

    if end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date.")

    for t in reminder_times:
        try:
            datetime.strptime(t, "%H:%M")
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid reminder time '{t}'. Use HH:MM format.")

    reminder = models.MedicineReminder(
        patient_id=patient.id,
        prescribed_by=None,
        medicine_name=medicine_name.strip(),
        dosage=dosage.strip(),
        frequency=freq_lower,
        reminder_times=reminder_times,
        start_date=start_date,
        end_date=end_date,
        instructions=instructions,
        source="self_added",
        is_active=True,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def record_adherence(
    db: Session,
    reminder: models.MedicineReminder,
    patient: models.User,
    dose_time: datetime,
    dose_status: str,
    notes: Optional[str],
) -> models.MedicineAdherence:
    """Patient reports a taken/skipped/missed dose."""
    # Verify ownership
    if reminder.patient_id != patient.id:
        raise HTTPException(status_code=403, detail="You can only record adherence for your own reminders.")

    if dose_status not in ALLOWED_DOSE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid dose status. Must be one of: {sorted(ALLOWED_DOSE_STATUSES)}",
        )

    adh = models.MedicineAdherence(
        reminder_id=reminder.id,
        patient_id=patient.id,
        dose_time=dose_time,
        status=dose_status,
        notes=notes,
    )
    db.add(adh)
    db.commit()
    db.refresh(adh)
    return adh


def deactivate_reminder(
    db: Session,
    reminder: models.MedicineReminder,
    actor: models.User,
) -> models.MedicineReminder:
    """Deactivate a reminder. Doctors may deactivate their own; patients may deactivate self_added."""
    if actor.role == "patient":
        if reminder.source != "self_added" or reminder.patient_id != actor.id:
            raise HTTPException(status_code=403, detail="Patients can only deactivate their own self-added reminders.")
    else:
        # Doctor: must be prescriber or admin
        if actor.role != "admin" and reminder.prescribed_by != actor.id:
            raise HTTPException(status_code=403, detail="Not authorized to deactivate this reminder.")

    reminder.is_active = False
    db.commit()
    db.refresh(reminder)

    if actor.role in ("doctor", "admin"):
        create_audit_event(
            db, actor_id=actor.id,
            action="reminder_deactivated",
            target_id=reminder.id,
        )
    return reminder


def serialize_reminder(r: models.MedicineReminder) -> dict:
    is_active = r.is_active
    if isinstance(is_active, str):
        is_active = is_active.lower() in ("true", "1")
    else:
        is_active = bool(is_active)

    return {
        "id": r.id,
        "patient_id": r.patient_id,
        "prescribed_by": r.prescribed_by,
        "medicine_name": r.medicine_name,
        "dosage": r.dosage,
        "frequency": r.frequency,
        "reminder_times": r.reminder_times,
        "start_date": r.start_date.isoformat() if r.start_date else None,
        "end_date": r.end_date.isoformat() if r.end_date else None,
        "instructions": r.instructions,
        "source": r.source,
        "is_active": is_active,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
