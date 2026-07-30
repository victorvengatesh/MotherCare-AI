# trackers.py — Fetal Kick Count & Contraction Timer Router for MotherCare AI v2.1
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.routes.ai import _get_or_create_twin
from app.schemas.response import StandardResponse

router = APIRouter(prefix="/trackers", tags=["Trackers"])
logger = logging.getLogger("trackers-route")


# ── Schemas ───────────────────────────────────────────────────────────────────

class KickSessionRequest(BaseModel):
    duration_seconds: int
    kick_count: int
    completed: bool = True

class ContractionLogRequest(BaseModel):
    duration_seconds: int
    interval_seconds: int
    intensity: str  # "mild", "moderate", "severe"


# ── Kick Counter Endpoints ───────────────────────────────────────────────────

@router.post("/kick/session")
async def log_kick_session(
    body: KickSessionRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logs a completed fetal movement kick-count session to the digital twin."""
    twin = _get_or_create_twin(db, current_user.id)
    
    if not twin.biomarkers:
        twin.biomarkers = {}
        
    kick_sessions = twin.biomarkers.get("kick_sessions", [])
    new_session = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "duration_seconds": body.duration_seconds,
        "kick_count": body.kick_count,
        "completed": body.completed
    }
    kick_sessions.append(new_session)
    
    # Store updated sessions back in JSON
    twin.biomarkers["kick_sessions"] = kick_sessions
    
    try:
        db.add(twin)
        db.commit()
        logger.info(f"Logged fetal kick session for user {current_user.id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to log kick session: {e}")
        raise HTTPException(status_code=500, detail="Database save failed.")

    return StandardResponse(status="success", data=new_session)


@router.get("/kick/history")
async def get_kick_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all historical kick counting sessions."""
    twin = _get_or_create_twin(db, current_user.id)
    kick_sessions = twin.biomarkers.get("kick_sessions", []) if twin.biomarkers else []
    return StandardResponse(status="success", data=kick_sessions)


# ── Contraction Timer Endpoints ──────────────────────────────────────────────

@router.post("/contraction/log")
async def log_contraction(
    body: ContractionLogRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logs a single uterine contraction event to calculate trends."""
    twin = _get_or_create_twin(db, current_user.id)
    
    if not twin.biomarkers:
        twin.biomarkers = {}
        
    contractions = twin.biomarkers.get("contractions", [])
    new_contraction = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "duration_seconds": body.duration_seconds,
        "interval_seconds": body.interval_seconds,
        "intensity": body.intensity
    }
    contractions.append(new_contraction)
    
    twin.biomarkers["contractions"] = contractions
    
    try:
        db.add(twin)
        db.commit()
        logger.info(f"Logged contraction event for user {current_user.id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to log contraction: {e}")
        raise HTTPException(status_code=500, detail="Database save failed.")

    return StandardResponse(status="success", data=new_contraction)


@router.get("/contraction/history")
async def get_contraction_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves the history of all logged contractions."""
    twin = _get_or_create_twin(db, current_user.id)
    contractions = twin.biomarkers.get("contractions", []) if twin.biomarkers else []
    return StandardResponse(status="success", data=contractions)
