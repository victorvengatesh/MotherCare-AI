import json
from datetime import datetime
from pathlib import Path
import uuid
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.db.database import SessionLocal
from app.db import models

def migrate():
    db = SessionLocal()
    json_path = Path(__file__).resolve().parent.parent.parent / "data" / "patient_history.json"
    if not json_path.exists():
        print("patient_history.json not found.")
        return

    # First ensure we have a default user to attach these records to
    user = db.query(models.User).filter_by(username="legacy_patient").first()
    if not user:
        user = models.User(
            username="legacy_patient",
            email="legacy@mothercare.ai",
            hashed_password="fake",
            role="patient"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    count = 0
    for r in records:
        content = f"Symptoms: {r.get('symptoms')}\nCondition: {r.get('condition')}\nAdvice: {r.get('advice')}"
        ts_str = r.get("timestamp")
        try:
            ts = datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()
        except:
            ts = datetime.utcnow()

        record = models.HealthRecord(
            id=str(uuid.uuid4()),
            user_id=user.id,
            data_type="legacy_json",
            content=content,
            summary=f"Urgency: {r.get('urgency')}",
            meta={"original": r},
            timestamp=ts
        )
        db.add(record)
        count += 1
    
    db.commit()
    print(f"Migrated {count} records to PostgreSQL.")

if __name__ == "__main__":
    migrate()
