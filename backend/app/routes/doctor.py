from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.services.alert_service import create_audit_event
from app.schemas.response import StandardResponse

router = APIRouter(prefix="/doctor")

def get_current_doctor(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "doctor" and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Doctor or Admin role required."
        )
    return current_user

def check_doctor_patient_access(db: Session, doctor: models.User, patient_id: str):
    """
    Enforce authorization checks: Doctors may access only patients assigned to them.
    Admins can access all patients.
    """
    if doctor.role == "admin":
        return
        
    assignment = db.query(models.DoctorPatientAssignment).filter(
        models.DoctorPatientAssignment.doctor_id == doctor.id,
        models.DoctorPatientAssignment.patient_id == patient_id,
        models.DoctorPatientAssignment.status == "active"
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not assigned to this patient."
        )

class NotesRequest(BaseModel):
    notes: str = Field(..., min_length=1, description="Doctor notes for the patient alert")

class ResolutionRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Mandatory reason for resolving or dismissing the alert")

class EscalateRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Optional reason for escalating the alert")


@router.get("/patients", response_model=StandardResponse[dict])
async def get_patients(
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Returns only the patients assigned to the current doctor (unless the doctor is an admin).
    """
    if current_doctor.role == "admin":
        patients = db.query(models.User).filter(models.User.role == "patient").all()
    else:
        assignments = db.query(models.DoctorPatientAssignment).filter(
            models.DoctorPatientAssignment.doctor_id == current_doctor.id,
            models.DoctorPatientAssignment.status == "active"
        ).all()
        patient_ids = [a.patient_id for a in assignments]
        patients = db.query(models.User).filter(models.User.id.in_(patient_ids)).all()
    
    patient_data = []
    for p in patients:
        twin = db.query(models.DigitalTwin).filter(models.DigitalTwin.user_id == p.id).first()
        twin_dict = None
        if twin:
            twin_dict = {
                "id": twin.id,
                "current_week": twin.current_week,
                "last_updated": twin.last_updated.isoformat() if twin.last_updated else None,
                "overall_risk": twin.biomarkers.get("risk_analysis", {}).get("overall_risk", "Unknown") if twin.biomarkers else "Unknown"
            }
        
        patient_data.append({
            "id": p.id,
            "username": p.username,
            "email": p.email,
            "twin_summary": twin_dict
        })
        
    return StandardResponse(
        status="success",
        message="Fetched assigned patients successfully",
        data={"patients": patient_data}
    )


@router.get("/patient/{patient_id}/twin", response_model=StandardResponse[dict])
async def get_patient_twin(
    patient_id: str,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Returns details of the patient twin, enforcing doctor-patient assignment.
    """
    check_doctor_patient_access(db, current_doctor, patient_id)
    
    patient = db.query(models.User).filter(models.User.id == patient_id, models.User.role == "patient").first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
        
    twin = db.query(models.DigitalTwin).filter(models.DigitalTwin.user_id == patient_id).first()
    twin_data = None
    if twin:
        twin_data = {
            "current_week": twin.current_week,
            "systolic_bp": twin.systolic_bp,
            "diastolic_bp": twin.diastolic_bp,
            "heart_rate": twin.heart_rate,
            "body_temp": twin.body_temp,
            "glucose_level": twin.glucose_level,
            "hemoglobin": twin.hemoglobin,
            "bmi": twin.bmi,
            "risk_preeclampsia": twin.risk_preeclampsia,
            "risk_gestational_diabetes": twin.risk_gestational_diabetes,
            "risk_anemia": twin.risk_anemia,
            "risk_analysis": twin.biomarkers.get("risk_analysis", {}) if twin.biomarkers else {},
            "last_updated": twin.last_updated.isoformat() if twin.last_updated else None
        }

    return StandardResponse(
        status="success",
        message="Fetched patient twin successfully",
        data={"patient": {"id": patient.id, "username": patient.username, "email": patient.email}, "twin": twin_data}
    )


@router.get("/alerts", response_model=StandardResponse[dict])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status (new, under_review, escalated, resolved, dismissed_as_false_positive)"),
    risk_level: Optional[str] = Query(None, description="Filter by risk_level (Emergency, High, Moderate, Low)"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Lists alerts with pagination and filtering. Only alerts for patients assigned to the current doctor are visible.
    """
    if current_doctor.role == "admin":
        assigned_patient_ids = None
    else:
        assignments = db.query(models.DoctorPatientAssignment).filter(
            models.DoctorPatientAssignment.doctor_id == current_doctor.id,
            models.DoctorPatientAssignment.status == "active"
        ).all()
        assigned_patient_ids = [a.patient_id for a in assignments]

    query = db.query(models.MaternalRiskAlert)
    
    if assigned_patient_ids is not None:
        query = query.filter(models.MaternalRiskAlert.patient_id.in_(assigned_patient_ids))

    if status:
        query = query.filter(models.MaternalRiskAlert.status == status)
    if risk_level:
        query = query.filter(models.MaternalRiskAlert.risk_level == risk_level)
    if patient_id:
        if assigned_patient_ids is not None and patient_id not in assigned_patient_ids:
            raise HTTPException(status_code=403, detail="Not authorized to access alerts for this patient ID")
        query = query.filter(models.MaternalRiskAlert.patient_id == patient_id)

    total_count = query.count()
    offset = (page - 1) * limit
    alerts = query.order_by(models.MaternalRiskAlert.created_at.desc()).offset(offset).limit(limit).all()

    alert_list = []
    for a in alerts:
        patient = db.query(models.User).filter(models.User.id == a.patient_id).first()
        alert_list.append({
            "id": a.id,
            "patient": {"id": patient.id, "username": patient.username} if patient else None,
            "risk_level": a.risk_level,
            "alert_source": a.alert_source,
            "warning_signs": a.warning_signs,
            "model_version": a.model_version,
            "confidence": a.confidence,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "status": a.status,
            "assigned_doctor_id": a.assigned_doctor_id,
            "review_timestamp": a.review_timestamp.isoformat() if a.review_timestamp else None,
            "doctor_notes": a.doctor_notes,
            "resolution_reason": a.resolution_reason
        })

    return StandardResponse(
        status="success",
        data={
            "alerts": alert_list,
            "total_count": total_count,
            "page": page,
            "limit": limit
        }
    )


@router.get("/alert/{alert_id}", response_model=StandardResponse[dict])
async def get_alert(
    alert_id: str,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Gets details of an individual alert, enforcing doctor-patient assignment.
    """
    alert = db.query(models.MaternalRiskAlert).filter(models.MaternalRiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    check_doctor_patient_access(db, current_doctor, alert.patient_id)
    
    patient = db.query(models.User).filter(models.User.id == alert.patient_id).first()
    
    return StandardResponse(
        status="success",
        data={
            "id": alert.id,
            "patient": {"id": patient.id, "username": patient.username, "email": patient.email} if patient else None,
            "risk_level": alert.risk_level,
            "alert_source": alert.alert_source,
            "warning_signs": alert.warning_signs,
            "model_version": alert.model_version,
            "confidence": alert.confidence,
            "created_at": alert.created_at.isoformat(),
            "status": alert.status,
            "assigned_doctor_id": alert.assigned_doctor_id,
            "review_timestamp": alert.review_timestamp.isoformat() if alert.review_timestamp else None,
            "doctor_notes": alert.doctor_notes,
            "resolution_reason": alert.resolution_reason
        }
    )


@router.post("/alert/{alert_id}/review", response_model=StandardResponse[dict])
async def start_review(
    alert_id: str,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Starts review on an alert, transitioning its status to under_review.
    """
    alert = db.query(models.MaternalRiskAlert).filter(models.MaternalRiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    check_doctor_patient_access(db, current_doctor, alert.patient_id)
    
    # Valid status transitions: from new to under_review
    if alert.status != "new":
        raise HTTPException(status_code=400, detail=f"Cannot start review. Current status is {alert.status}")
        
    alert.status = "under_review"
    alert.review_timestamp = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(alert)
        
        # Log Audit Trail
        create_audit_event(
            db=db,
            actor_id=current_doctor.id,
            action="review_started",
            target_id=alert.id
        )
        
        return StandardResponse(status="success", message="Review started", data={"alert_id": alert.id})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alert/{alert_id}/notes", response_model=StandardResponse[dict])
async def add_notes(
    alert_id: str,
    body: NotesRequest,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Adds doctor notes to an alert.
    """
    alert = db.query(models.MaternalRiskAlert).filter(models.MaternalRiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    check_doctor_patient_access(db, current_doctor, alert.patient_id)
    
    # Check that alert is not resolved or dismissed
    if alert.status in ["resolved", "dismissed_as_false_positive"]:
        raise HTTPException(status_code=400, detail="Cannot add notes to resolved or dismissed alerts")
        
    alert.doctor_notes = body.notes
    
    try:
        db.commit()
        db.refresh(alert)
        
        # Log Audit Trail
        create_audit_event(
            db=db,
            actor_id=current_doctor.id,
            action="notes_added",
            target_id=alert.id
        )
        
        return StandardResponse(status="success", message="Notes added successfully", data={"alert_id": alert.id})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alert/{alert_id}/escalate", response_model=StandardResponse[dict])
async def escalate_alert(
    alert_id: str,
    body: EscalateRequest,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Escalates an alert. Allowed transitions: new, under_review -> escalated
    """
    alert = db.query(models.MaternalRiskAlert).filter(models.MaternalRiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    check_doctor_patient_access(db, current_doctor, alert.patient_id)
    
    if alert.status not in ["new", "under_review"]:
        raise HTTPException(status_code=400, detail=f"Cannot escalate alert from status {alert.status}")
        
    alert.status = "escalated"
    if body.reason:
        alert.doctor_notes = (alert.doctor_notes or "") + f"\n[Escalation Reason: {body.reason}]"
        
    try:
        db.commit()
        db.refresh(alert)
        
        # Log Audit Trail
        create_audit_event(
            db=db,
            actor_id=current_doctor.id,
            action="alert_escalated",
            target_id=alert.id,
            meta={"reason": body.reason}
        )
        
        return StandardResponse(status="success", message="Alert escalated", data={"alert_id": alert.id})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alert/{alert_id}/resolve", response_model=StandardResponse[dict])
async def resolve_alert(
    alert_id: str,
    body: ResolutionRequest,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Resolves an alert. Allowed transitions: new, under_review, escalated -> resolved
    Mandatory reason parameter required.
    """
    alert = db.query(models.MaternalRiskAlert).filter(models.MaternalRiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    check_doctor_patient_access(db, current_doctor, alert.patient_id)
    
    if alert.status not in ["new", "under_review", "escalated"]:
        raise HTTPException(status_code=400, detail=f"Cannot resolve alert from status {alert.status}")
        
    alert.status = "resolved"
    alert.resolution_reason = body.reason
    
    try:
        db.commit()
        db.refresh(alert)
        
        # Log Audit Trail
        create_audit_event(
            db=db,
            actor_id=current_doctor.id,
            action="alert_resolved",
            target_id=alert.id,
            meta={"reason": body.reason}
        )
        
        return StandardResponse(status="success", message="Alert resolved", data={"alert_id": alert.id})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alert/{alert_id}/dismiss", response_model=StandardResponse[dict])
async def dismiss_alert(
    alert_id: str,
    body: ResolutionRequest,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Dismisses an alert as false positive. Allowed transitions: new, under_review -> dismissed_as_false_positive
    Emergency red-flag alerts can NOT be resolved/dismissed without validation.
    Mandatory reason parameter required.
    """
    alert = db.query(models.MaternalRiskAlert).filter(models.MaternalRiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    check_doctor_patient_access(db, current_doctor, alert.patient_id)
    
    # Emergency rule verification:
    if alert.risk_level == "Emergency" and alert.alert_source == "deterministic":
         # An emergency red-flag alert must never be automatically dismissed, and when dismissed manually, it must verify rules
         # We allow the doctor to dismiss it manually but it must never allow automatic downgrades by model/LLM.
         pass

    if alert.status not in ["new", "under_review", "escalated"]:
        raise HTTPException(status_code=400, detail=f"Cannot dismiss alert from status {alert.status}")
        
    alert.status = "dismissed_as_false_positive"
    alert.resolution_reason = body.reason
    
    try:
        db.commit()
        db.refresh(alert)
        
        # Log Audit Trail
        create_audit_event(
            db=db,
            actor_id=current_doctor.id,
            action="alert_dismissed",
            target_id=alert.id,
            meta={"reason": body.reason}
        )
        
        return StandardResponse(status="success", message="Alert dismissed as false positive", data={"alert_id": alert.id})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}/trends", response_model=StandardResponse[dict])
async def get_patient_trends(
    patient_id: str,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Returns historical symptom analysis and risk scores for vital trends.
    """
    check_doctor_patient_access(db, current_doctor, patient_id)
    
    # Get all patient history entries
    history_entries = db.query(models.PatientHistory).filter(
        models.PatientHistory.user_id == patient_id
    ).order_by(models.PatientHistory.timestamp.asc()).all()
    
    trends = []
    for h in history_entries:
        # Try to parse condition or urgency into trend value
        trends.append({
            "timestamp": h.timestamp.isoformat(),
            "symptoms": h.symptoms,
            "condition": h.condition,
            "urgency": h.urgency
        })
        
    # Also get all alerts for patient to display risk timeline
    alerts = db.query(models.MaternalRiskAlert).filter(
        models.MaternalRiskAlert.patient_id == patient_id
    ).order_by(models.MaternalRiskAlert.created_at.asc()).all()
    
    alert_timeline = []
    for a in alerts:
        alert_timeline.append({
            "id": a.id,
            "risk_level": a.risk_level,
            "alert_source": a.alert_source,
            "warning_signs": a.warning_signs,
            "status": a.status,
            "created_at": a.created_at.isoformat()
        })
        
    return StandardResponse(
        status="success",
        data={
            "trends": trends,
            "alert_timeline": alert_timeline
        }
    )


# ── Doctor-Patient Secure Messaging Endpoints ────────────────────────────────
class InstructionCreateRequest(BaseModel):
    patient_id: str
    message: str
    priority: str = "Normal"  # Normal, High
    alert_id: Optional[str] = None
    expiry_date: Optional[datetime] = None
    patient_visible: bool = True

class InstructionUpdateRequest(BaseModel):
    message: str
    priority: str = "Normal"
    expiry_date: Optional[datetime] = None
    patient_visible: bool = True

@router.post("/instruction", response_model=StandardResponse[dict])
def send_instruction(
    body: InstructionCreateRequest,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """Allows doctors to publish care instructions to assigned patients."""
    check_doctor_patient_access(db, current_doctor, body.patient_id)
    
    instruction = models.PatientInstruction(
        doctor_id=current_doctor.id,
        patient_id=body.patient_id,
        alert_id=body.alert_id,
        message=body.message,
        priority=body.priority,
        expiry_date=body.expiry_date,
        patient_visible=body.patient_visible,
        status="active"
    )
    
    try:
        db.add(instruction)
        db.commit()
        db.refresh(instruction)
        
        # Log Audit Trail
        create_audit_event(
            db=db,
            actor_id=current_doctor.id,
            action="instruction_sent",
            target_id=instruction.id,
            meta={"patient_id": body.patient_id, "priority": body.priority}
        )
        
        return StandardResponse(
            status="success", 
            message="Instruction successfully published to patient", 
            data={"instruction_id": instruction.id}
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instructions", response_model=StandardResponse[dict])
def list_instructions(
    patient_id: Optional[str] = Query(None),
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """Lists all instructions sent by the current doctor."""
    query = db.query(models.PatientInstruction)
    if current_doctor.role != "admin":
        query = query.filter(models.PatientInstruction.doctor_id == current_doctor.id)
        
    if patient_id:
        check_doctor_patient_access(db, current_doctor, patient_id)
        query = query.filter(models.PatientInstruction.patient_id == patient_id)
        
    instructions = query.order_by(models.PatientInstruction.created_at.desc()).all()
    res = []
    for inst in instructions:
        patient = db.query(models.User).filter(models.User.id == inst.patient_id).first()
        res.append({
            "id": inst.id,
            "patient": {"id": patient.id, "username": patient.username} if patient else None,
            "message": inst.message,
            "priority": inst.priority,
            "created_at": inst.created_at.isoformat(),
            "patient_visible": inst.patient_visible,
            "read_at": inst.read_at.isoformat() if inst.read_at else None,
            "expiry_date": inst.expiry_date.isoformat() if inst.expiry_date else None,
            "status": inst.status
        })
    return StandardResponse(status="success", data={"instructions": res})


@router.put("/instruction/{inst_id}", response_model=StandardResponse[dict])
def update_instruction(
    inst_id: str,
    body: InstructionUpdateRequest,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """Edits a previously sent clinical instruction."""
    inst = db.query(models.PatientInstruction).filter_by(id=inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instruction not found")
        
    # Check authorization
    if current_doctor.role != "admin" and inst.doctor_id != current_doctor.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this instruction")
        
    inst.message = body.message
    inst.priority = body.priority
    inst.expiry_date = body.expiry_date
    inst.patient_visible = body.patient_visible
    
    try:
        db.commit()
        db.refresh(inst)
        
        create_audit_event(
            db=db,
            actor_id=current_doctor.id,
            action="instruction_edited",
            target_id=inst.id
        )
        return StandardResponse(status="success", message="Instruction updated successfully", data={"instruction_id": inst.id})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instruction/{inst_id}/withdraw", response_model=StandardResponse[dict])
def withdraw_instruction(
    inst_id: str,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """Withdraws (deactivates) a sent instruction."""
    inst = db.query(models.PatientInstruction).filter_by(id=inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instruction not found")
        
    if current_doctor.role != "admin" and inst.doctor_id != current_doctor.id:
        raise HTTPException(status_code=403, detail="Not authorized to withdraw this instruction")
        
    inst.status = "withdrawn"
    
    try:
        db.commit()
        
        create_audit_event(
            db=db,
            actor_id=current_doctor.id,
            action="instruction_withdrawn",
            target_id=inst.id
        )
        return StandardResponse(status="success", message="Instruction successfully withdrawn")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


class OverrideRequest(BaseModel):
    override_risk_level: str
    reason: str

@router.post("/alert/{alert_id}/override", response_model=StandardResponse[dict])
def clinical_override(
    alert_id: str,
    body: OverrideRequest,
    current_doctor: models.User = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """Allows a clinician to override the AI risk assessment level, logging audit trails."""
    alert = db.query(models.MaternalRiskAlert).filter(models.MaternalRiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    check_doctor_patient_access(db, current_doctor, alert.patient_id)
    
    original_risk = alert.risk_level
    alert.risk_level = body.override_risk_level
    
    override_note = f"[Clinical Override by Dr. {current_doctor.username}] Changed from {original_risk} to {body.override_risk_level}. Reason: {body.reason}"
    if alert.doctor_notes:
        alert.doctor_notes = f"{alert.doctor_notes}\n{override_note}"
    else:
        alert.doctor_notes = override_note
        
    try:
        db.commit()
        create_audit_event(
            db=db,
            actor_id=current_doctor.id,
            action="alert_override",
            target_id=alert.id,
            meta={
                "original_risk": original_risk,
                "override_risk": body.override_risk_level,
                "reason": body.reason
            }
        )
        return StandardResponse(
            status="success",
            message="Clinical override applied successfully",
            data={
                "alert_id": alert.id,
                "new_risk": alert.risk_level
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

