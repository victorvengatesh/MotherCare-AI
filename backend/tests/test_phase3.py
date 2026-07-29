import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.db import models
from app.services.auth_service import create_access_token, hash_password
from app.services.alert_service import process_symptom_alert, process_twin_alerts

# Setup a test SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase3.db"
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


def test_role_boundaries_and_authorization(client):
    # Patient trying to list doctor patients should get 403
    headers = get_auth_headers("patient1")
    response = client.get("/doctor/patients", headers=headers)
    assert response.status_code == 403

    # Doctor trying to access admin assignments should get 403
    headers = get_auth_headers("doctor1")
    response = client.get("/admin/assignments", headers=headers)
    assert response.status_code == 403

    # Admin should be allowed
    headers = get_auth_headers("admin_user")
    response = client.get("/admin/assignments", headers=headers)
    print("STATUS:", response.status_code)
    print("BODY:", response.json())
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_doctor_patient_assignment_workflow(client, test_db):
    headers = get_auth_headers("admin_user")
    
    # Create active assignment
    payload = {"doctor_id": "doc1-id", "patient_id": "pat1-id"}
    response = client.post("/admin/assign", json=payload, headers=headers)
    assert response.status_code == 200
    
    # Doctor 1 lists patients - patient1 should be returned
    doc_headers = get_auth_headers("doctor1")
    response = client.get("/doctor/patients", headers=doc_headers)
    assert response.status_code == 200
    patients = response.json()["data"]["patients"]
    assert len(patients) == 1
    assert patients[0]["id"] == "pat1-id"

    # Doctor 2 lists patients - should return 0 patients
    doc2_headers = get_auth_headers("doctor2")
    response = client.get("/doctor/patients", headers=doc2_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]["patients"]) == 0

    # Doctor 2 accesses patient 1 twin - should be 403 Forbidden
    response = client.get("/doctor/patient/pat1-id/twin", headers=doc2_headers)
    assert response.status_code == 403

    # Doctor 1 accesses patient 1 twin - should be 200
    response = client.get("/doctor/patient/pat1-id/twin", headers=doc_headers)
    assert response.status_code == 200


def test_alert_creation_from_deterministic_emergency_rules(client, test_db):
    # Establish doctor assignment first
    admin_headers = get_auth_headers("admin_user")
    client.post("/admin/assign", json={"doctor_id": "doc1-id", "patient_id": "pat1-id"}, headers=admin_headers)

    # Perform analyze request with emergency symptoms
    pat_headers = get_auth_headers("patient1")
    response = client.post(
        "/analyze",
        data={"symptoms": "romba ratham varuthu (heavy bleeding)"},
        headers=pat_headers
    )
    assert response.status_code == 200

    # Verify alert is created in database
    alerts = test_db.query(models.MaternalRiskAlert).filter_by(patient_id="pat1-id").all()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.risk_level == "Emergency"
    assert alert.alert_source == "deterministic"
    assert alert.assigned_doctor_id == "doc1-id"
    assert alert.status == "new"


def test_alert_creation_from_high_risk_ml_output(client, test_db):
    # Establish doctor assignment
    admin_headers = get_auth_headers("admin_user")
    client.post("/admin/assign", json={"doctor_id": "doc1-id", "patient_id": "pat1-id"}, headers=admin_headers)

    # Trigger process_twin_alerts directly
    # BP 160/110 -> High risk Pre-eclampsia, Hemoglobin 8.0 -> High risk Anaemia
    twin_data = {
        "systolic_bp": 160,
        "diastolic_bp": 110,
        "glucose_level": 180,
        "hemoglobin": 8.0,
        "heart_rate": 105,
        "body_temp": 98.6,
        "bmi": 32,
        "current_week": 24
    }
    risks = {
        "risk_scores": {"pre_eclampsia": 0.85, "gestational_diabetes": 0.75, "anemia": 0.90},
        "overall_risk": "High"
    }

    process_twin_alerts(test_db, "pat1-id", twin_data, risks)

    # Verify alerts exist
    alerts = test_db.query(models.MaternalRiskAlert).filter_by(patient_id="pat1-id").all()
    # Should have a vitals alert and an ml alert
    sources = [a.alert_source for a in alerts]
    assert "vitals" in sources
    assert "ml" in sources


def test_low_confidence_clinical_review_alert(client, test_db):
    # Probability 0.52 (Confidence = 0.52, i.e., < 0.6)
    twin_data = {
        "systolic_bp": 125,
        "diastolic_bp": 82,
        "glucose_level": 112,
        "hemoglobin": 11.5,
        "heart_rate": 78,
        "body_temp": 98.6,
        "bmi": 24,
        "current_week": 18
    }
    risks = {
        "risk_scores": {"pre_eclampsia": 0.52, "gestational_diabetes": 0.30, "anemia": 0.20},
        "overall_risk": "Moderate"
    }

    process_twin_alerts(test_db, "pat1-id", twin_data, risks)
    
    # Verify low-confidence alert created
    alerts = test_db.query(models.MaternalRiskAlert).filter_by(patient_id="pat1-id").all()
    ml_alerts = [a for a in alerts if a.alert_source == "ml" and "Low Confidence" in a.warning_signs]
    assert len(ml_alerts) == 1
    assert ml_alerts[0].risk_level == "Moderate"


def test_alert_status_transitions_and_mandatory_reasons(client, test_db):
    # Setup alert
    alert = models.MaternalRiskAlert(
        id="alert-test-id",
        patient_id="pat1-id",
        risk_level="High",
        alert_source="ml",
        warning_signs="High pre-eclampsia risk",
        status="new"
    )
    assignment = models.DoctorPatientAssignment(
        doctor_id="doc1-id",
        patient_id="pat1-id",
        status="active",
        assigned_by="admin"
    )
    test_db.add_all([alert, assignment])
    test_db.commit()

    doc_headers = get_auth_headers("doctor1")

    # Transition: new -> under_review
    response = client.post("/doctor/alert/alert-test-id/review", headers=doc_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Review started"

    # Try resolving without reason - should fail validation
    response = client.post("/doctor/alert/alert-test-id/resolve", json={}, headers=doc_headers)
    assert response.status_code == 422 # FastAPI validation error

    # Resolve with reason - should succeed
    response = client.post("/doctor/alert/alert-test-id/resolve", json={"reason": "Patient BP stabilized after review"}, headers=doc_headers)
    assert response.status_code == 200
    
    # Verify DB state
    db_alert = test_db.query(models.MaternalRiskAlert).filter_by(id="alert-test-id").first()
    assert db_alert.status == "resolved"
    assert db_alert.resolution_reason == "Patient BP stabilized after review"


def test_audit_event_creation(client, test_db):
    # Establish assignment
    admin_headers = get_auth_headers("admin_user")
    response = client.post("/admin/assign", json={"doctor_id": "doc1-id", "patient_id": "pat1-id"}, headers=admin_headers)
    assert response.status_code == 200

    # Verify assignment change audit event exists
    audit_events = test_db.query(models.AuditTrail).filter_by(action="doctor_patient_assignment_changed").all()
    assert len(audit_events) == 1
    assert audit_events[0].actor_id == "admin-id"


def test_pagination_and_filtering(client, test_db):
    # Setup doctor assignment
    admin_headers = get_auth_headers("admin_user")
    client.post("/admin/assign", json={"doctor_id": "doc1-id", "patient_id": "pat1-id"}, headers=admin_headers)

    # Add 12 dummy alerts
    for i in range(12):
        alert = models.MaternalRiskAlert(
            patient_id="pat1-id",
            risk_level="High" if i % 2 == 0 else "Moderate",
            alert_source="ml",
            warning_signs=f"Symptom warning {i}",
            status="new" if i < 8 else "under_review"
        )
        test_db.add(alert)
    test_db.commit()

    doc_headers = get_auth_headers("doctor1")
    
    # Request page 1 with limit 5
    response = client.get("/doctor/alerts?page=1&limit=5", headers=doc_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["alerts"]) == 5
    assert data["total_count"] == 12

    # Filter by status "under_review"
    response = client.get("/doctor/alerts?status=under_review", headers=doc_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["alerts"]) == 4
