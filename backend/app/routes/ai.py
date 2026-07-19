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

    from app.schemas.response import StandardResponse
    return StandardResponse(
        status="success",
        data={
            **twin_data,
            "risk_analysis": risks,
            "username": current_user.username,
            "language": current_user.language,
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
    from app.schemas.response import StandardResponse
    return StandardResponse(status="success", data={**_twin_to_dict(twin), "risk_analysis": risks})


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
