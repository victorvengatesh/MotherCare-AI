import json
import os
from datetime import datetime
from pathlib import Path

# Path to history storage
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
HISTORY_FILE = PROJECT_ROOT / "data" / "patient_history.json"

# Ensure data directory exists
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

def _load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def check_similarity(current_symptoms: str) -> bool:
    """
    Checks if current symptoms are similar to any previous entry.
    Simple keyword overlap logic.
    """
    history = _load_history()
    if not history:
        return False

    current_words = set(_tokenize(current_symptoms))
    if not current_words:
        return False

    for entry in history:
        prev_words = set(_tokenize(entry.get("symptoms", "")))
        overlap = current_words.intersection(prev_words)
        # If 2 or more significant keywords match, consider it similar
        if len(overlap) >= 2:
            return True
    
    return False

def add_to_history(symptoms: str, analysis_result: dict):
    """
    Saves a new entry into the patient history.
    """
    history = _load_history()
    
    new_entry = {
        "symptoms": symptoms,
        "condition": analysis_result.get("condition"),
        "urgency": analysis_result.get("urgency"),
        "advice": analysis_result.get("advice"),
        "timestamp": datetime.now().isoformat()
    }
    
    history.append(new_entry)
    _save_history(history)

def _tokenize(text: str):
    """
    Basic tokenization: lowercase, remove special chars, filter short words.
    """
    stop_words = {"and", "the", "with", "have", "you", "are", "for", "that", "this", "some"}
    words = text.lower().replace(",", " ").replace(".", " ").replace("!", " ").split()
    return [w for w in words if len(w) > 2 and w not in stop_words]
