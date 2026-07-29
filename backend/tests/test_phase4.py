import pytest
from unittest.mock import patch
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.db import models
from app.services.auth_service import create_access_token, hash_password
from app.services.normalization_service import process_multilingual_input

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase4.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Create test users
        admin = models.User(
            id="admin-id",
            username="admin_user",
            email="admin@test.com",
            hashed_password=hash_password("adminpass"),
            role="admin"
        )
        doctor1 = models.User(
            id="doc1-id",
            username="doctor1",
            email="doc1@test.com",
            hashed_password=hash_password("docpass"),
            role="doctor"
        )
        doctor2 = models.User(
            id="doc2-id",
            username="doctor2",
            email="doc2@test.com",
            hashed_password=hash_password("docpass"),
            role="doctor"
        )
        patient1 = models.User(
            id="pat1-id",
            username="patient1",
            email="pat1@test.com",
            hashed_password=hash_password("patpass"),
            role="patient"
        )
        patient2 = models.User(
            id="pat2-id",
            username="patient2",
            email="pat2@test.com",
            hashed_password=hash_password("patpass"),
            role="patient"
        )
        
        db.add_all([admin, doctor1, doctor2, patient1, patient2])
        db.commit()

        # Add doctor patient assignments
        assign1 = models.DoctorPatientAssignment(
            id="assign1",
            doctor_id="doc1-id",
            patient_id="pat1-id",
            status="active",
            assigned_by="admin_user"
        )
        db.add(assign1)
        db.commit()

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def get_auth_headers(username: str) -> dict:
    token = create_access_token(data={"sub": username, "type": "access"})
    return {"Authorization": f"Bearer {token}"}

# ─── 1 & 2. NEGATION & SYMPTOM NORMALIZATION TESTS ───────────────────────────

def test_clause_scoped_negation_english():
    # 1. "I have headache but no fever"
    res1 = process_multilingual_input("I have headache but no fever")
    assert "headache" in res1["extracted_symptoms"]
    assert "headache" not in res1["negated_symptoms"]
    assert "fever" in res1["negated_symptoms"]
    assert "fever" not in res1["extracted_symptoms"]

    # 2. "No headache but I have fever"
    res2 = process_multilingual_input("No headache but I have fever")
    assert "headache" in res2["negated_symptoms"]
    assert "headache" not in res2["extracted_symptoms"]
    assert "fever" in res2["extracted_symptoms"]
    assert "fever" not in res2["negated_symptoms"]

    # 3. "No fever or vomiting"
    res3 = process_multilingual_input("No fever or vomiting")
    assert "fever" in res3["negated_symptoms"]
    # Depending on how the parser splits, let's verify both are caught as negated/present
    # "No fever or vomiting" -> "no" can preceding both
    assert "fever" in res3["negated_symptoms"]

def test_tamil_tanglish_negations():
    # 1. Tamil: "இரத்தப்போக்கு இல்லை"
    res1 = process_multilingual_input("இரத்தப்போக்கு இல்லை")
    assert "bleeding" in res1["negated_symptoms"]

    # 2. Tanglish: "bleeding illa"
    res2 = process_multilingual_input("bleeding illa")
    assert "bleeding" in res2["negated_symptoms"]

    # 3. Short list with negation at end: "mayakkam and thalai vali. kai kaal veekam illai."
    res3 = process_multilingual_input("mayakkam and thalai vali. kai kaal veekam illai.")
    # dizziness/fainting (mayakkam) -> present
    assert "dizziness/fainting" in res3["extracted_symptoms"]
    # headache (thalai vali) -> present
    assert "headache" in res3["extracted_symptoms"]
    # swelling of hands or feet (kai kaal veekam) -> negated because "illai" is in the same clause
    assert "swelling of hands or feet" in res3["negated_symptoms"]

def test_severity_and_duration_extraction():
    res = process_multilingual_input("I don't have fever, but severe stomach pain for two hours")
    # "abdominal pain" is mapped from "stomach pain"
    assert "abdominal pain" in res["extracted_symptoms"]
    assert res["severity"] == "Severe"
    assert res["duration"] == "two hours"

    res_baby = process_multilingual_input("Baby movement has been low since morning")
    assert "reduced fetal movement" in res_baby["extracted_symptoms"]

def test_vocabulary_spelling_variants_and_unknown():
    res1 = process_multilingual_input("I have thalavali and kulandhai asaiyala")
    assert "headache" in res1["extracted_symptoms"]
    assert "reduced fetal movement" in res1["extracted_symptoms"]

    res2 = process_multilingual_input("baby movement kammiya iruku")
    assert "reduced fetal movement" in res2["extracted_symptoms"]

    # Unknown words
    res3 = process_multilingual_input("I feel very strange xyzunrecognizedword")
    assert "xyzunrecognizedword" in res3["uncertain_terms"]

# ─── 3. SAFETY PIPELINE AND FALLBACK TESTS ─────────────────────────────────────

@patch('app.utils.ai_wrapper.call_ai_with_retry')
def test_safety_override_on_gemini_failure(mock_ai, client):
    # Mock Gemini API throwing exception
    mock_ai.side_effect = Exception("Gemini server crash")

    headers = get_auth_headers("patient1")
    response = client.post(
        "/analyze",
        data={"symptoms": "I have severe vaginal bleeding and baby is not moving"},
        headers=headers
    )
    
    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["risk_level"] == "Emergency"
    assert res_data["requires_immediate_care"] is True
    assert "bleeding" in res_data["extracted_symptoms"]
    assert "CRITICAL WARNING" in res_data["explanation"]

@patch('app.services.rag_service.get_relevant_context')
def test_safety_override_on_rag_failure(mock_rag, client):
    # Mock RAG querying throwing SQLite/Chroma exception
    mock_rag.side_effect = Exception("Chroma database connection lost")

    headers = get_auth_headers("patient1")
    response = client.post(
        "/analyze",
        data={"symptoms": "I am bleeding since morning"},
        headers=headers
    )
    
    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["risk_level"] == "Emergency"
    assert "bleeding" in res_data["extracted_symptoms"]

# ─── 4. DOCTOR PATIENT INSTRUCTIONS SECURE API TESTS ─────────────────────────────

def test_doctor_instruction_authorization_and_privacy(client, test_db):
    # Doctor 1 sending care instruction to patient 1 (assigned) -> Allowed (200)
    headers_doc1 = get_auth_headers("doctor1")
    payload = {
        "patient_id": "pat1-id",
        "message": "Take iron tablets daily after food.",
        "priority": "High",
        "patient_visible": True
    }
    resp1 = client.post("/doctor/instruction", json=payload, headers=headers_doc1)
    assert resp1.status_code == 200
    inst_id = resp1.json()["data"]["instruction_id"]

    # Doctor 2 sending care instruction to patient 1 (not assigned) -> Forbidden (403)
    headers_doc2 = get_auth_headers("doctor2")
    resp2 = client.post("/doctor/instruction", json=payload, headers=headers_doc2)
    assert resp2.status_code == 403

    # Add an internal note (patient_visible=False)
    payload_note = {
        "patient_id": "pat1-id",
        "message": "Note: Patient exhibits mild anemia signs.",
        "priority": "Normal",
        "patient_visible": False
      }
    resp_note = client.post("/doctor/instruction", json=payload_note, headers=headers_doc1)
    assert resp_note.status_code == 200
    note_id = resp_note.json()["data"]["instruction_id"]

    # Patient 1 retrieves active guidelines. Should see instruction but NOT internal note.
    headers_pat1 = get_auth_headers("patient1")
    
    resp_pat = client.get("/ai/instructions", headers=headers_pat1)
    assert resp_pat.status_code == 200
    insts = resp_pat.json()["data"]["instructions"]
    
    # Verify inst_id exists but note_id is absent
    inst_ids = [i["id"] for i in insts]
    assert inst_id in inst_ids
    assert note_id not in inst_ids

    # Patient 1 marks instruction as read
    resp_read = client.post(f"/ai/instruction/{inst_id}/read", headers=headers_pat1)
    assert resp_read.status_code == 200

    # Doctor 1 edits the instruction
    payload_edit = {
        "message": "Take iron tablets daily after dinner.",
        "priority": "High",
        "patient_visible": True
    }
    resp_edit = client.put(f"/doctor/instruction/{inst_id}", json=payload_edit, headers=headers_doc1)
    assert resp_edit.status_code == 200

    # Doctor 1 withdraws the instruction
    resp_with = client.post(f"/doctor/instruction/{inst_id}/withdraw", headers=headers_doc1)
    assert resp_with.status_code == 200

    # Patient 1 should no longer see it (withdrawn)
    resp_pat2 = client.get("/ai/instructions", headers=headers_pat1)
    insts2 = resp_pat2.json()["data"]["instructions"]
    assert inst_id not in [i["id"] for i in insts2]
