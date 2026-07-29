"""Medicine reminders API routes for MotherCare AI.

Safety rules:
- Only assigned doctors may create doctor-sourced reminders.
- Patients may only create self_added reminders for themselves.
- Gemini / AI must never prescribe.
- No cross-patient data exposure.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.services.reminder_service import (
    create_doctor_reminder, create_self_reminder,
    record_adherence, deactivate_reminder, serialize_reminder,
    ALLOWED_FREQUENCIES, ALLOWED_DOSE_STATUSES,
)
from app.schemas.response import StandardResponse

router = APIRouter(prefix="/reminders", tags=["Medicine Reminders"])


class DoctorReminderRequest(BaseModel):
    patient_id: str
    medicine_name: str = Field(..., min_length=1)
    dosage: str = Field(..., min_length=1)
    frequency: str
    reminder_times: List[str] = Field(default_factory=list)
    start_date: datetime
    end_date: Optional[datetime] = None
    instructions: Optional[str] = None


class SelfReminderRequest(BaseModel):
    medicine_name: str = Field(..., min_length=1)
    dosage: str = Field(..., min_length=1)
    frequency: str
    reminder_times: List[str] = Field(default_factory=list)
    start_date: datetime
    end_date: Optional[datetime] = None
    instructions: Optional[str] = None


class AdherenceRequest(BaseModel):
    dose_time: datetime
    status: str = Field(..., description="taken | skipped | missed")
    notes: Optional[str] = None


@router.post("/doctor", response_model=StandardResponse[dict])
async def doctor_create_reminder(
    body: DoctorReminderRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Doctor creates a prescription reminder for an assigned patient."""
    if current_user.role not in ("doctor", "admin"):
        raise HTTPException(status_code=403, detail="Doctor or Admin role required.")

    reminder = create_doctor_reminder(
        db=db,
        doctor=current_user,
        patient_id=body.patient_id,
        medicine_name=body.medicine_name,
        dosage=body.dosage,
        frequency=body.frequency,
        reminder_times=body.reminder_times,
        start_date=body.start_date,
        end_date=body.end_date,
        instructions=body.instructions,
    )
    return StandardResponse(
        status="success",
        message="Medicine reminder created.",
        data=serialize_reminder(reminder),
    )


@router.post("/self", response_model=StandardResponse[dict])
async def patient_create_self_reminder(
    body: SelfReminderRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Patient creates a personal self-care reminder (labelled self_added)."""
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients may create self-added reminders.")

    reminder = create_self_reminder(
        db=db,
        patient=current_user,
        medicine_name=body.medicine_name,
        dosage=body.dosage,
        frequency=body.frequency,
        reminder_times=body.reminder_times,
        start_date=body.start_date,
        end_date=body.end_date,
        instructions=body.instructions,
    )
    return StandardResponse(
        status="success",
        message="Self reminder created.",
        data=serialize_reminder(reminder),
    )


@router.get("", response_model=StandardResponse[dict])
async def list_reminders(
    patient_id: Optional[str] = None,
    active_only: bool = True,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List medicine reminders. Patients see their own; doctors see assigned patients'."""
    if current_user.role == "patient":
        target_id = current_user.id
    elif current_user.role in ("doctor", "admin"):
        if not patient_id:
            raise HTTPException(status_code=422, detail="patient_id is required for doctor/admin.")
        # Verify doctor-patient access
        if current_user.role == "doctor":
            assignment = db.query(models.DoctorPatientAssignment).filter_by(
                doctor_id=current_user.id, patient_id=patient_id, status="active"
            ).first()
            if not assignment:
                raise HTTPException(status_code=403, detail="Access denied.")
        target_id = patient_id
    else:
        raise HTTPException(status_code=403, detail="Access denied.")

    q = db.query(models.MedicineReminder).filter_by(patient_id=target_id)
    reminders = q.order_by(models.MedicineReminder.created_at.desc()).all()

    if active_only:
        def _is_active(r):
            v = r.is_active
            if isinstance(v, str):
                return v.lower() in ("true", "1")
            return bool(v)
        reminders = [r for r in reminders if _is_active(r)]

    return StandardResponse(
        status="success",
        data={"reminders": [serialize_reminder(r) for r in reminders]},
    )


@router.post("/{reminder_id}/adherence", response_model=StandardResponse[dict])
async def record_dose_adherence(
    reminder_id: str,
    body: AdherenceRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Patient marks a dose as taken, skipped, or missed."""
    reminder = db.query(models.MedicineReminder).filter_by(id=reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found.")

    adh = record_adherence(
        db=db,
        reminder=reminder,
        patient=current_user,
        dose_time=body.dose_time,
        dose_status=body.status,
        notes=body.notes,
    )
    return StandardResponse(
        status="success",
        message="Dose status recorded.",
        data={
            "id": adh.id,
            "status": adh.status,
            "dose_time": adh.dose_time.isoformat(),
            "recorded_at": adh.recorded_at.isoformat(),
        },
    )


@router.post("/{reminder_id}/deactivate", response_model=StandardResponse[dict])
async def deactivate_reminder_endpoint(
    reminder_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deactivate a reminder (doctor or patient for self_added)."""
    reminder = db.query(models.MedicineReminder).filter_by(id=reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found.")

    deactivated = deactivate_reminder(db=db, reminder=reminder, actor=current_user)
    return StandardResponse(
        status="success",
        message="Reminder deactivated.",
        data=serialize_reminder(deactivated),
    )
