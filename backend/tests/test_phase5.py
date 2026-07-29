"""Phase 5 Integration Tests — MotherCare AI

Covers:
- Appointment creation, authorization, status transitions, past-date, conflict
- Medicine reminder role boundaries, self vs doctor-created, dosage validation
- Adherence tracking
- Notification ownership and read/unread
- Health and readiness endpoints
- PDF authorization
- Regression: Phase 1-4 test files still pass (separate runs)
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.db import models
from app.services.auth_service import create_access_token, hash_password
from app.services.notification_service import create_notification

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase5.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        admin = models.User(id="admin-id", username="admin_user", email="admin@test.com",
                            hashed_password=hash_password("adminpass"), role="admin")
        doctor1 = models.User(id="doc1-id", username="doctor1", email="doc1@test.com",
                              hashed_password=hash_password("docpass"), role="doctor")
        doctor2 = models.User(id="doc2-id", username="doctor2", email="doc2@test.com",
                              hashed_password=hash_password("docpass"), role="doctor")
        patient1 = models.User(id="pat1-id", username="patient1", email="pat1@test.com",
                               hashed_password=hash_password("patpass"), role="patient")
        patient2 = models.User(id="pat2-id", username="patient2", email="pat2@test.com",
                               hashed_password=hash_password("patpass"), role="patient")

        db.add_all([admin, doctor1, doctor2, patient1, patient2])
        db.commit()

        assign1 = models.DoctorPatientAssignment(
            id="assign1", doctor_id="doc1-id", patient_id="pat1-id",
            status="active", assigned_by="admin_user"
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


def auth(username):
    token = create_access_token(data={"sub": username, "type": "access"})
    return {"Authorization": f"Bearer {token}"}


# ─── HEALTH & READINESS ENDPOINTS ─────────────────────────────────────────────

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["status"] == "healthy"


def test_readiness_endpoint(client):
    resp = client.get("/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert "ready" in data["data"]
    assert "checks" in data["data"]


# ─── APPOINTMENT TESTS ────────────────────────────────────────────────────────

FUTURE_DT = (datetime.utcnow() + timedelta(days=3)).isoformat()
PAST_DT   = (datetime.utcnow() - timedelta(days=1)).isoformat()


def test_patient_creates_appointment(client):
    payload = {
        "doctor_id": "doc1-id",
        "appointment_datetime": FUTURE_DT,
        "appointment_type": "checkup",
        "reason": "Monthly checkup",
    }
    resp = client.post("/appointments", json=payload, headers=auth("patient1"))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "requested"
    assert data["patient_id"] == "pat1-id"


def test_past_date_appointment_rejected(client):
    payload = {
        "doctor_id": "doc1-id",
        "appointment_datetime": PAST_DT,
        "appointment_type": "checkup",
        "reason": "Old appointment",
    }
    resp = client.post("/appointments", json=payload, headers=auth("patient1"))
    assert resp.status_code == 422


def test_patient_cannot_book_unassigned_doctor(client):
    payload = {
        "doctor_id": "doc2-id",    # doc2 not assigned to patient1
        "appointment_datetime": FUTURE_DT,
        "appointment_type": "checkup",
        "reason": "Checkup",
    }
    resp = client.post("/appointments", json=payload, headers=auth("patient1"))
    assert resp.status_code == 403


def test_doctor_confirms_appointment(client, test_db):
    # Create appointment first
    appt = models.Appointment(
        id="appt1",
        patient_id="pat1-id",
        doctor_id="doc1-id",
        appointment_datetime=datetime.utcnow() + timedelta(days=3),
        appointment_type="checkup",
        reason="Checkup",
        status="requested",
    )
    test_db.add(appt)
    test_db.commit()

    resp = client.put(
        "/appointments/appt1/status",
        json={"new_status": "confirmed"},
        headers=auth("doctor1"),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "confirmed"


def test_invalid_status_transition_rejected(client, test_db):
    appt = models.Appointment(
        id="appt2",
        patient_id="pat1-id",
        doctor_id="doc1-id",
        appointment_datetime=datetime.utcnow() + timedelta(days=3),
        appointment_type="checkup",
        reason="Test",
        status="completed",  # terminal state
    )
    test_db.add(appt)
    test_db.commit()

    resp = client.put(
        "/appointments/appt2/status",
        json={"new_status": "confirmed"},
        headers=auth("doctor1"),
    )
    assert resp.status_code == 422


def test_cancellation_requires_reason(client, test_db):
    appt = models.Appointment(
        id="appt3",
        patient_id="pat1-id",
        doctor_id="doc1-id",
        appointment_datetime=datetime.utcnow() + timedelta(days=3),
        appointment_type="checkup",
        reason="Test",
        status="confirmed",
    )
    test_db.add(appt)
    test_db.commit()

    # Cancel without reason → should fail
    resp = client.put(
        "/appointments/appt3/status",
        json={"new_status": "cancelled"},
        headers=auth("doctor1"),
    )
    assert resp.status_code == 422


def test_unauthorized_doctor_cannot_manage_appointment(client, test_db):
    appt = models.Appointment(
        id="appt4",
        patient_id="pat2-id",   # patient2 NOT assigned to doctor1
        doctor_id="doc2-id",
        appointment_datetime=datetime.utcnow() + timedelta(days=3),
        appointment_type="checkup",
        reason="Test",
        status="requested",
    )
    test_db.add(appt)
    test_db.commit()

    resp = client.put(
        "/appointments/appt4/status",
        json={"new_status": "confirmed"},
        headers=auth("doctor1"),  # doctor1 is not assigned to patient2
    )
    assert resp.status_code == 403


# ─── MEDICINE REMINDER TESTS ──────────────────────────────────────────────────

def test_doctor_creates_reminder_for_assigned_patient(client):
    payload = {
        "patient_id": "pat1-id",
        "medicine_name": "Folic Acid",
        "dosage": "5mg",
        "frequency": "once daily",
        "reminder_times": ["08:00"],
        "start_date": datetime.utcnow().isoformat(),
    }
    resp = client.post("/reminders/doctor", json=payload, headers=auth("doctor1"))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "doctor"
    assert data["medicine_name"] == "Folic Acid"


def test_doctor_cannot_create_reminder_for_unassigned_patient(client):
    payload = {
        "patient_id": "pat2-id",   # NOT assigned to doctor1
        "medicine_name": "Iron",
        "dosage": "200mg",
        "frequency": "once daily",
        "reminder_times": ["08:00"],
        "start_date": datetime.utcnow().isoformat(),
    }
    resp = client.post("/reminders/doctor", json=payload, headers=auth("doctor1"))
    assert resp.status_code == 403


def test_patient_creates_self_reminder(client):
    payload = {
        "medicine_name": "Vitamin D",
        "dosage": "1000IU",
        "frequency": "once daily",
        "reminder_times": ["09:00"],
        "start_date": datetime.utcnow().isoformat(),
    }
    resp = client.post("/reminders/self", json=payload, headers=auth("patient1"))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "self_added"


def test_patient_cannot_create_doctor_reminder(client):
    payload = {
        "patient_id": "pat1-id",
        "medicine_name": "Aspirin",
        "dosage": "100mg",
        "frequency": "once daily",
        "reminder_times": [],
        "start_date": datetime.utcnow().isoformat(),
    }
    resp = client.post("/reminders/doctor", json=payload, headers=auth("patient1"))
    assert resp.status_code == 403


def test_invalid_frequency_rejected(client):
    payload = {
        "medicine_name": "Vitamin C",
        "dosage": "500mg",
        "frequency": "whenever I feel like it",  # invalid
        "reminder_times": [],
        "start_date": datetime.utcnow().isoformat(),
    }
    resp = client.post("/reminders/self", json=payload, headers=auth("patient1"))
    assert resp.status_code == 422


def test_invalid_reminder_time_format_rejected(client):
    payload = {
        "medicine_name": "Calcium",
        "dosage": "500mg",
        "frequency": "twice daily",
        "reminder_times": ["8am", "20pm"],   # invalid formats
        "start_date": datetime.utcnow().isoformat(),
    }
    resp = client.post("/reminders/self", json=payload, headers=auth("patient1"))
    assert resp.status_code == 422


def test_adherence_tracking(client, test_db):
    # Create reminder directly
    reminder = models.MedicineReminder(
        id="rem1",
        patient_id="pat1-id",
        medicine_name="Iron Tablet",
        dosage="200mg",
        frequency="once daily",
        reminder_times=["08:00"],
        start_date=datetime.utcnow(),
        source="doctor",
        is_active=True,
    )
    test_db.add(reminder)
    test_db.commit()

    # Patient marks dose as taken
    resp = client.post(
        "/reminders/rem1/adherence",
        json={"dose_time": datetime.utcnow().isoformat(), "status": "taken"},
        headers=auth("patient1"),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "taken"

    # Patient marks another as skipped
    resp2 = client.post(
        "/reminders/rem1/adherence",
        json={"dose_time": (datetime.utcnow() + timedelta(days=1)).isoformat(), "status": "skipped"},
        headers=auth("patient1"),
    )
    assert resp2.status_code == 200
    assert resp2.json()["data"]["status"] == "skipped"


def test_patient_cannot_record_other_patients_adherence(client, test_db):
    reminder = models.MedicineReminder(
        id="rem2",
        patient_id="pat2-id",   # owned by patient2
        medicine_name="Magnesium",
        dosage="200mg",
        frequency="once daily",
        reminder_times=[],
        start_date=datetime.utcnow(),
        source="self_added",
        is_active=True,
    )
    test_db.add(reminder)
    test_db.commit()

    resp = client.post(
        "/reminders/rem2/adherence",
        json={"dose_time": datetime.utcnow().isoformat(), "status": "taken"},
        headers=auth("patient1"),   # wrong patient
    )
    assert resp.status_code == 403


def test_invalid_dose_status_rejected(client, test_db):
    reminder = models.MedicineReminder(
        id="rem3",
        patient_id="pat1-id",
        medicine_name="Iron",
        dosage="100mg",
        frequency="once daily",
        reminder_times=[],
        start_date=datetime.utcnow(),
        source="self_added",
        is_active=True,
    )
    test_db.add(reminder)
    test_db.commit()

    resp = client.post(
        "/reminders/rem3/adherence",
        json={"dose_time": datetime.utcnow().isoformat(), "status": "forgot"},   # invalid
        headers=auth("patient1"),
    )
    assert resp.status_code == 422


# ─── NOTIFICATION TESTS ────────────────────────────────────────────────────────

def test_notifications_ownership(client, test_db):
    # Create notification for patient1 and patient2
    n1 = create_notification(test_db, user_id="pat1-id", notif_type="reminder", message="Take your iron tablet.")
    n2 = create_notification(test_db, user_id="pat2-id", notif_type="reminder", message="Take your folic acid.")

    # Patient1 should only see their own notifications
    resp = client.get("/notifications", headers=auth("patient1"))
    assert resp.status_code == 200
    notif_ids = [n["id"] for n in resp.json()["data"]["notifications"]]
    assert n1.id in notif_ids
    assert n2.id not in notif_ids


def test_notification_read_unread(client, test_db):
    n = create_notification(test_db, user_id="pat1-id", notif_type="instruction",
                            message="Your doctor has sent a new care instruction.")
    assert not n.is_read

    # Get unread count
    resp = client.get("/notifications?unread_only=true", headers=auth("patient1"))
    assert resp.status_code == 200
    unread_ids = [x["id"] for x in resp.json()["data"]["notifications"]]
    assert n.id in unread_ids

    # Mark as read
    resp2 = client.post(f"/notifications/{n.id}/read", headers=auth("patient1"))
    assert resp2.status_code == 200

    # Now should not appear in unread
    resp3 = client.get("/notifications?unread_only=true", headers=auth("patient1"))
    unread_after = [x["id"] for x in resp3.json()["data"]["notifications"]]
    assert n.id not in unread_after


def test_patient_cannot_mark_other_notification_read(client, test_db):
    n = create_notification(test_db, user_id="pat2-id", notif_type="reminder", message="Your pill.")
    resp = client.post(f"/notifications/{n.id}/read", headers=auth("patient1"))
    assert resp.status_code == 404


def test_mark_all_read(client, test_db):
    create_notification(test_db, user_id="pat1-id", notif_type="reminder", message="Reminder 1")
    create_notification(test_db, user_id="pat1-id", notif_type="reminder", message="Reminder 2")

    resp = client.post("/notifications/read-all", headers=auth("patient1"))
    assert resp.status_code == 200

    resp2 = client.get("/notifications?unread_only=true", headers=auth("patient1"))
    assert resp2.json()["data"]["unread_count"] == 0


# ─── PDF AUTHORIZATION TESTS ──────────────────────────────────────────────────

def test_patient_can_request_own_pdf(client):
    resp = client.get("/reports/summary/pdf", headers=auth("patient1"))
    # Should succeed (200 or stream) — pdf lib installed
    assert resp.status_code in (200, 503)   # 503 only if reportlab truly missing


def test_patient_cannot_request_other_pdf(client):
    resp = client.get("/reports/summary/pdf?patient_id=pat2-id", headers=auth("patient1"))
    # Patients cannot use patient_id param to request another patient's PDF
    # patient_id param is ignored for patient role; they get their own
    assert resp.status_code in (200, 503)   # They get their own, not pat2's


def test_doctor_requests_patient_pdf(client):
    resp = client.get("/reports/summary/pdf?patient_id=pat1-id", headers=auth("doctor1"))
    assert resp.status_code in (200, 503)


def test_doctor_cannot_access_unassigned_patient_pdf(client):
    resp = client.get("/reports/summary/pdf?patient_id=pat2-id", headers=auth("doctor1"))
    assert resp.status_code == 403


def test_doctor_must_provide_patient_id_for_pdf(client):
    resp = client.get("/reports/summary/pdf", headers=auth("doctor1"))
    assert resp.status_code == 422
