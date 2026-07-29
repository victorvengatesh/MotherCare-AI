"""
AI Routes — Multi-Agent Chat, PDF Upload, Digital Twin CRUD
"""
import uuid
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.services.rag_service import process_pdf, index_patient_data
from app.agents.orchestrator import run_consultation
from app.services.risk_engine import MaternalRiskEngine
from app.schemas.response import StandardResponse

router = APIRouter(prefix="/ai", tags=["AI"])
logger = logging.getLogger("ai-routes")

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

risk_engine = MaternalRiskEngine()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    language: str = "English"   # "English" or "Tamil"


class TwinUpdateRequest(BaseModel):
    current_week:     float | None = None
    due_date:         str   | None = None
    systolic_bp:      float | None = None
    diastolic_bp:     float | None = None
    heart_rate:       float | None = None
    body_temp:        float | None = None
    glucose_level:    float | None = None
    hemoglobin:       float | None = None
    iron_level:       float | None = None
    bmi:              float | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_twin(db: Session, user_id: str) -> models.DigitalTwin:
    twin = db.query(models.DigitalTwin).filter_by(user_id=user_id).first()
    if not twin:
        twin = models.DigitalTwin(id=str(uuid.uuid4()), user_id=user_id)
        try:
            db.add(twin)
            db.commit()
            db.refresh(twin)
        except Exception as e:
            db.rollback()
            logger.exception("Failed to create twin: %s", e)
            raise HTTPException(status_code=500, detail="Database error creating twin.")
    return twin


def _twin_to_dict(twin: models.DigitalTwin) -> dict:
    return {
        "current_week":    twin.current_week,
        "due_date":        twin.due_date,
        "systolic_bp":     twin.systolic_bp,
        "diastolic_bp":    twin.diastolic_bp,
        "heart_rate":      twin.heart_rate,
        "body_temp":       twin.body_temp,
        "glucose_level":   twin.glucose_level,
        "hemoglobin":      twin.hemoglobin,
        "iron_level":      twin.iron_level,
        "bmi":             twin.bmi,
        "biomarkers":      twin.biomarkers or {},
        "risk_preeclampsia":         twin.risk_preeclampsia,
        "risk_gestational_diabetes": twin.risk_gestational_diabetes,
        "risk_anemia":               twin.risk_anemia,
        "last_updated":    twin.last_updated.isoformat() if twin.last_updated else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Multi-Agent consultation endpoint with RAG context injection."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    twin = _get_or_create_twin(db, current_user.id)
    twin_data = _twin_to_dict(twin)

    # Use user's saved language preference if not overridden
    language = body.language or current_user.language or "English"

    result = run_consultation(
        query=body.query,
        user_id=current_user.id,
        twin_data=twin_data,
        language=language,
        db=db,
    )

    # Save to health records
    record = models.HealthRecord(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        data_type="chat",
        content=body.query,
        summary=result["response"][:500],
        meta={"agent": result["agent"], "language": language},
    )
    try:
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Failed to save chat record: %s", e)
        raise HTTPException(status_code=500, detail="Database error saving chat record.")

    from app.schemas.response import StandardResponse
    return StandardResponse(status="success", data=result)


@router.post("/upload-report")
async def upload_report(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a PDF health report — extracts, summarises, and indexes in RAG."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Extract text
    text = await process_pdf(file)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from PDF.")

    # Index into ChromaDB for RAG
    chunks = index_patient_data(text, current_user.id, filename=file.filename)

    # Generate summary via Gemini
    summary = _summarise_report(text, current_user.language or "English")

    # Persist record
    record = models.HealthRecord(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        data_type="report",
        filename=file.filename,
        content=text[:2000],
        summary=summary,
        meta={"chunks_indexed": chunks},
    )
    try:
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Failed to save report record: %s", e)
        raise HTTPException(status_code=500, detail="Database error saving report record.")

    from app.schemas.response import StandardResponse
    return StandardResponse(
        status="success",
        data={
            "filename":       file.filename,
            "chunks_indexed": chunks,
            "summary":        summary,
        },
    )


def _summarise_report(text: str, language: str) -> str:
    import os
    from google import genai
    from app.utils.ai_wrapper import call_ai_with_retry

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Summary unavailable — Gemini API key not configured."

    lang_note = "Respond in Tamil (தமிழ்)." if language == "Tamil" else "Respond in English."
    prompt = (
        f"You are a medical report analyst. Summarise the following health report "
        f"in 4–6 plain-language bullet points that a patient can understand. "
        f"Highlight any abnormal values. {lang_note}\n\n{text[:4000]}"
    )
    
    client = genai.Client(api_key=api_key)
    
    summary = call_ai_with_retry(
        client=client,
        model="gemini-2.5-flash",
        contents=prompt,
        agent_name="report_summariser",
        fallback_text="Summary generation failed. Please review the report manually."
    )
    return summary


@router.get("/twin")
def get_twin(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the current user's Digital Twin state with live risk scores."""
    twin = _get_or_create_twin(db, current_user.id)
    twin_data = _twin_to_dict(twin)

    # Compute fresh risk scores
    risks = risk_engine.predict_risks(twin_data)

    # Process alerts based on vitals and ML risks
    from app.services.alert_service import process_twin_alerts
    process_twin_alerts(db, current_user.id, twin_data, risks)

    # Persist updated risk scores
    try:
        twin.risk_preeclampsia         = risks["risk_scores"]["pre_eclampsia"]
        twin.risk_gestational_diabetes = risks["risk_scores"]["gestational_diabetes"]
        twin.risk_anemia               = risks["risk_scores"]["anemia"]
        twin.last_updated              = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Failed to update twin risks: %s", e)
        raise HTTPException(status_code=500, detail="Database error updating twin risks.")

    # Check for active alerts awaiting doctor review
    active_alert = db.query(models.MaternalRiskAlert).filter(
        models.MaternalRiskAlert.patient_id == current_user.id,
        models.MaternalRiskAlert.status.in_(["new", "under_review", "escalated"])
    ).first()
    awaiting_review = active_alert is not None
    review_status = active_alert.status if active_alert else None

    from app.schemas.response import StandardResponse
    return StandardResponse(
        status="success",
        data={
            **twin_data,
            "risk_analysis": risks,
            "username": current_user.username,
            "language": current_user.language,
            "awaiting_review": awaiting_review,
            "review_status": review_status
        },
    )


@router.put("/twin")
def update_twin(
    body: TwinUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update biomarker values on the Digital Twin."""
    twin = _get_or_create_twin(db, current_user.id)

    for field, value in body.model_dump(exclude_none=True).items():
        if hasattr(twin, field):
            setattr(twin, field, value)

    try:
        twin.last_updated = datetime.utcnow()
        db.commit()
        db.refresh(twin)
    except Exception as e:
        db.rollback()
        logger.exception("Failed to update twin: %s", e)
        raise HTTPException(status_code=500, detail="Database error updating twin.")

    risks = risk_engine.predict_risks(_twin_to_dict(twin))
    
    from app.services.alert_service import process_twin_alerts
    process_twin_alerts(db, current_user.id, _twin_to_dict(twin), risks)
    
    # Check for active alerts awaiting doctor review
    active_alert = db.query(models.MaternalRiskAlert).filter(
        models.MaternalRiskAlert.patient_id == current_user.id,
        models.MaternalRiskAlert.status.in_(["new", "under_review", "escalated"])
    ).first()
    awaiting_review = active_alert is not None
    review_status = active_alert.status if active_alert else None
    
    from app.schemas.response import StandardResponse
    return StandardResponse(status="success", data={
        **_twin_to_dict(twin), 
        "risk_analysis": risks,
        "awaiting_review": awaiting_review,
        "review_status": review_status
    })


@router.get("/records")
def get_records(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns all health records (chat history + uploaded reports) for the user."""
    records = (
        db.query(models.HealthRecord)
        .filter_by(user_id=current_user.id)
        .order_by(models.HealthRecord.timestamp.desc())
        .limit(50)
        .all()
    )
    from app.schemas.response import StandardResponse
    return StandardResponse(
        status="success",
        data=[
            {
                "id":        r.id,
                "type":      r.data_type,
                "filename":  r.filename,
                "summary":   r.summary,
                "meta":      r.meta,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in records
        ],
    )


@router.get("/trends", response_model=StandardResponse[dict])
def get_user_trends(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns historical screening and risk logs for the current patient.
    """
    history_entries = db.query(models.PatientHistory).filter(
        models.PatientHistory.user_id == current_user.id
    ).order_by(models.PatientHistory.timestamp.asc()).all()
    
    trends = []
    for h in history_entries:
        trends.append({
            "timestamp": h.timestamp.isoformat(),
            "symptoms": h.symptoms,
            "condition": h.condition,
            "urgency": h.urgency
        })
        
    alerts = db.query(models.MaternalRiskAlert).filter(
        models.MaternalRiskAlert.patient_id == current_user.id
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


# ── Patient Care Instructions Messaging Endpoints ──────────────────────────────
@router.get("/instructions", response_model=StandardResponse[dict])
def get_patient_instructions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all active clinical instructions published for the current patient."""
    now = datetime.utcnow()
    
    # Query active instructions that haven't expired
    instructions = (
        db.query(models.PatientInstruction)
        .filter(
            models.PatientInstruction.patient_id == current_user.id,
            models.PatientInstruction.status == "active",
            (models.PatientInstruction.expiry_date == None) | (models.PatientInstruction.expiry_date > now)
        )
        .order_by(models.PatientInstruction.created_at.desc())
        .all()
    )
    
    res = []
    for inst in instructions:
        # Perform safe python visibility check (SQLite JSON types store boolean as 'true' or 1 or true)
        vis = inst.patient_visible
        if isinstance(vis, str):
            is_visible = vis.lower() in ("true", "1")
        elif isinstance(vis, int):
            is_visible = bool(vis)
        else:
            is_visible = bool(vis)
            
        if not is_visible:
            continue

        doctor = db.query(models.User).filter(models.User.id == inst.doctor_id).first()
        res.append({
            "id": inst.id,
            "doctor_name": doctor.username if doctor else "Healthcare Provider",
            "message": inst.message,
            "priority": inst.priority,
            "created_at": inst.created_at.isoformat(),
            "read_at": inst.read_at.isoformat() if inst.read_at else None,
            "expiry_date": inst.expiry_date.isoformat() if inst.expiry_date else None
        })
        
    return StandardResponse(status="success", data={"instructions": res})


@router.post("/instruction/{inst_id}/read", response_model=StandardResponse[dict])
def mark_instruction_read(
    inst_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marks a patient instruction as read by the patient."""
    inst = db.query(models.PatientInstruction).filter_by(id=inst_id, patient_id=current_user.id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instruction not found or access denied")
        
    if not inst.read_at:
        inst.read_at = datetime.utcnow()
        db.commit()
        
        # Log Audit Trail
        from app.services.alert_service import create_audit_event
        create_audit_event(
            db=db,
            actor_id=current_user.id,
            action="instruction_read",
            target_id=inst.id
        )
        
    return StandardResponse(status="success", message="Instruction marked as read")

