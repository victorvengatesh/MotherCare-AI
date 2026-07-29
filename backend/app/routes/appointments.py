"""Appointments API routes for MotherCare AI.

Auth rules:
- Patients may request appointments only for themselves.
- Doctors may manage appointments only for assigned patients.
- Valid status transitions enforced server-side.
- Reason required for cancellation / rescheduling.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.services.appointment_service import (
    create_appointment, update_appointment_status, serialize_appointment,
    assert_doctor_patient_access, VALID_TRANSITIONS, APPOINTMENT_TYPES,
)
from app.schemas.response import StandardResponse

router = APIRouter(prefix="/appointments", tags=["Appointments"])


class AppointmentRequest(BaseModel):
    doctor_id: str = Field(..., description="ID of the doctor to book with")
    appointment_datetime: datetime = Field(..., description="ISO datetime for appointment")
    appointment_type: str = Field(..., description="Type of appointment")
    reason: str = Field(..., min_length=3, description="Reason for appointment")

    @field_validator("appointment_type")
    @classmethod
    def validate_type(cls, v):
        if v not in APPOINTMENT_TYPES:
            raise ValueError(f"appointment_type must be one of: {sorted(APPOINTMENT_TYPES)}")
        return v


class StatusUpdateRequest(BaseModel):
    new_status: str = Field(..., description="New appointment status")
    reason: Optional[str] = Field(None, description="Required for cancellation/rescheduling")
    doctor_notes: Optional[str] = Field(None)
    patient_instructions: Optional[str] = Field(None)
    new_datetime: Optional[datetime] = Field(None, description="New time if rescheduling")


@router.post("", response_model=StandardResponse[dict])
async def request_appointment(
    body: AppointmentRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Patient requests a new appointment with their assigned doctor."""
    if current_user.role not in ("patient", "admin"):
        raise HTTPException(status_code=403, detail="Only patients may request appointments.")

    # Verify patient is actually assigned to this doctor
    if current_user.role == "patient":
        assignment = db.query(models.DoctorPatientAssignment).filter(
            models.DoctorPatientAssignment.doctor_id == body.doctor_id,
            models.DoctorPatientAssignment.patient_id == current_user.id,
            models.DoctorPatientAssignment.status == "active",
        ).first()
        if not assignment:
            raise HTTPException(
                status_code=403,
                detail="You can only request appointments with your assigned doctor.",
            )

    appt = create_appointment(
        db=db,
        patient_id=current_user.id,
        doctor_id=body.doctor_id,
        appointment_datetime=body.appointment_datetime,
        appointment_type=body.appointment_type,
        reason=body.reason,
        created_by=current_user,
    )
    return StandardResponse(
        status="success",
        message="Appointment requested successfully.",
        data=serialize_appointment(appt, include_private=False),
    )


@router.get("", response_model=StandardResponse[dict])
async def list_appointments(
    patient_id: Optional[str] = Query(None),
    appt_status: Optional[str] = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List appointments. Patients see their own; doctors see assigned patients'."""
    if current_user.role == "patient":
        target_patient_id = current_user.id
    elif current_user.role in ("doctor", "admin"):
        if not patient_id:
            # Return all patients' appointments for doctor
            if current_user.role == "admin":
                target_patient_id = None
            else:
                # Doctor: collect all their patients
                assignments = db.query(models.DoctorPatientAssignment).filter_by(
                    doctor_id=current_user.id, status="active"
                ).all()
                patient_ids = [a.patient_id for a in assignments]
                q = db.query(models.Appointment).filter(
                    models.Appointment.patient_id.in_(patient_ids)
                )
                if appt_status:
                    q = q.filter(models.Appointment.status == appt_status)
                appts = q.order_by(models.Appointment.appointment_datetime.desc()).limit(100).all()
                return StandardResponse(
                    status="success",
                    data={"appointments": [serialize_appointment(a, include_private=True) for a in appts]},
                )
        else:
            assert_doctor_patient_access(db, current_user, patient_id)
            target_patient_id = patient_id
    else:
        raise HTTPException(status_code=403, detail="Access denied.")

    q = db.query(models.Appointment)
    if target_patient_id:
        q = q.filter(models.Appointment.patient_id == target_patient_id)
    if appt_status:
        q = q.filter(models.Appointment.status == appt_status)

    appts = q.order_by(models.Appointment.appointment_datetime.desc()).limit(100).all()
    include_private = current_user.role in ("doctor", "admin")

    return StandardResponse(
        status="success",
        data={"appointments": [serialize_appointment(a, include_private=include_private) for a in appts]},
    )


@router.put("/{appt_id}/status", response_model=StandardResponse[dict])
async def update_status(
    appt_id: str,
    body: StatusUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Doctor updates appointment status. Patients may cancel their own 'requested' appointments."""
    appt = db.query(models.Appointment).filter_by(id=appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if current_user.role == "patient":
        # Patients may only cancel their own appointments
        if appt.patient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied.")
        if body.new_status != "cancelled":
            raise HTTPException(status_code=403, detail="Patients may only cancel appointments.")
    elif current_user.role in ("doctor", "admin"):
        assert_doctor_patient_access(db, current_user, appt.patient_id)
    else:
        raise HTTPException(status_code=403, detail="Access denied.")

    updated = update_appointment_status(
        db=db,
        appt=appt,
        new_status=body.new_status,
        actor=current_user,
        reason=body.reason,
        doctor_notes=body.doctor_notes,
        patient_instructions=body.patient_instructions,
        new_datetime=body.new_datetime,
    )
    include_private = current_user.role in ("doctor", "admin")
    return StandardResponse(
        status="success",
        message=f"Appointment status updated to '{body.new_status}'.",
        data=serialize_appointment(updated, include_private=include_private),
    )


@router.get("/{appt_id}", response_model=StandardResponse[dict])
async def get_appointment(
    appt_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a single appointment detail."""
    appt = db.query(models.Appointment).filter_by(id=appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if current_user.role == "patient" and appt.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    elif current_user.role == "doctor":
        assert_doctor_patient_access(db, current_user, appt.patient_id)

    include_private = current_user.role in ("doctor", "admin")
    return StandardResponse(
        status="success",
        data=serialize_appointment(appt, include_private=include_private),
    )
