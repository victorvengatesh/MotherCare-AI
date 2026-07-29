from datetime import datetime
from sqlalchemy.orm import Session
from app.db import models

def check_similarity(db: Session, user_id: str, current_symptoms: str) -> bool:
    """
    Checks if current symptoms are similar to any previous entry for this specific user.
    Simple keyword overlap logic.
    """
    history = db.query(models.PatientHistory).filter(models.PatientHistory.user_id == user_id).all()
    if not history:
        return False

    current_words = set(_tokenize(current_symptoms))
    if not current_words:
        return False

    for entry in history:
        prev_words = set(_tokenize(entry.symptoms))
        overlap = current_words.intersection(prev_words)
        # If 2 or more significant keywords match, consider it similar
        if len(overlap) >= 2:
            return True
    
    return False

def add_to_history(db: Session, user_id: str, symptoms: str, analysis_result: dict):
    """
    Saves a new entry into the patient history table.
    """
    new_entry = models.PatientHistory(
        user_id=user_id,
        symptoms=symptoms,
        condition=analysis_result.get("condition"),
        urgency=analysis_result.get("urgency"),
        advice=analysis_result.get("advice"),
        timestamp=datetime.utcnow()
    )
    try:
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger("history-service").exception("Failed to save history: %s", e)
        raise

def _tokenize(text: str):
    """
    Basic tokenization: lowercase, remove special chars, filter short words.
    """
    stop_words = {"and", "the", "with", "have", "you", "are", "for", "that", "this", "some"}
    words = text.lower().replace(",", " ").replace(".", " ").replace("!", " ").split()
    return [w for w in words if len(w) > 2 and w not in stop_words]
