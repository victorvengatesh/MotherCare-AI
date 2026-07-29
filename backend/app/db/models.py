import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Float, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="patient")          # patient, admin
    language = Column(String, default="English")       # English, Tamil
    created_at = Column(DateTime, default=datetime.utcnow)

    history_entries = relationship("PatientHistory", back_populates="user", cascade="all, delete-orphan")
    digital_twin    = relationship("DigitalTwin",    back_populates="user", uselist=False, cascade="all, delete-orphan")
    health_records  = relationship("HealthRecord",   back_populates="user", cascade="all, delete-orphan")
    
    assignments_as_doctor = relationship("DoctorPatientAssignment", foreign_keys="[DoctorPatientAssignment.doctor_id]", back_populates="doctor", cascade="all, delete-orphan")
    assignments_as_patient = relationship("DoctorPatientAssignment", foreign_keys="[DoctorPatientAssignment.patient_id]", back_populates="patient", cascade="all, delete-orphan")
    alerts = relationship("MaternalRiskAlert", foreign_keys="[MaternalRiskAlert.patient_id]", back_populates="patient", cascade="all, delete-orphan")
    
    instructions_sent = relationship("PatientInstruction", foreign_keys="[PatientInstruction.doctor_id]", back_populates="doctor", cascade="all, delete-orphan")
    instructions_received = relationship("PatientInstruction", foreign_keys="[PatientInstruction.patient_id]", back_populates="patient", cascade="all, delete-orphan")


class PatientHistory(Base):
    __tablename__ = "patient_history"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    symptoms   = Column(Text, nullable=False)
    condition  = Column(String, nullable=False)
    urgency    = Column(String, nullable=False)
    advice     = Column(Text, nullable=False)
    timestamp  = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="history_entries")


class DigitalTwin(Base):
    """Tracks 40+ maternal biomarkers as a live state machine."""
    __tablename__ = "digital_twins"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id         = Column(String, ForeignKey("users.id"), unique=True, nullable=False)

    # Pregnancy info
    current_week    = Column(Float, default=0.0)
    due_date        = Column(String, nullable=True)

    # Vitals
    systolic_bp     = Column(Float, default=120.0)
    diastolic_bp    = Column(Float, default=80.0)
    heart_rate      = Column(Float, default=75.0)
    body_temp       = Column(Float, default=98.6)

    # Labs
    glucose_level   = Column(Float, default=90.0)
    hemoglobin      = Column(Float, default=12.0)
    iron_level      = Column(Float, default=60.0)
    bmi             = Column(Float, default=22.0)

    # Extended biomarkers stored as JSON (flexible)
    biomarkers      = Column(JSON, default=dict)

    # Risk scores (0–1 probability)
    risk_preeclampsia        = Column(Float, default=0.0)
    risk_gestational_diabetes = Column(Float, default=0.0)
    risk_anemia              = Column(Float, default=0.0)

    last_updated    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="digital_twin")


class HealthRecord(Base):
    """Stores uploaded documents, reports, and their summaries."""
    __tablename__ = "health_records"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = Column(String, ForeignKey("users.id"), nullable=False)
    data_type   = Column(String, nullable=False)   # 'symptom', 'report', 'image_analysis'
    filename    = Column(String, nullable=True)
    content     = Column(Text, nullable=True)
    summary     = Column(Text, nullable=True)
    meta        = Column(JSON, default=dict)
    timestamp   = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="health_records")


class DoctorPatientAssignment(Base):
    __tablename__ = "doctor_patient_assignments"

    id             = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id      = Column(String, ForeignKey("users.id"), nullable=False)
    patient_id     = Column(String, ForeignKey("users.id"), nullable=False)
    status         = Column(String, default="active")  # active, inactive
    assigned_date  = Column(DateTime, default=datetime.utcnow)
    assigned_by    = Column(String, nullable=False)
    end_date       = Column(DateTime, nullable=True)

    # Relationships
    doctor         = relationship("User", foreign_keys=[doctor_id], back_populates="assignments_as_doctor")
    patient        = relationship("User", foreign_keys=[patient_id], back_populates="assignments_as_patient")

    __table_args__ = (
        UniqueConstraint('doctor_id', 'patient_id', name='_doctor_patient_uc'),
    )


class MaternalRiskAlert(Base):
    __tablename__ = "maternal_risk_alerts"

    id                 = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id         = Column(String, ForeignKey("users.id"), nullable=False)
    risk_level         = Column(String, nullable=False)  # High, Moderate, Low, Emergency
    alert_source       = Column(String, nullable=False)  # deterministic, ml, vitals
    warning_signs      = Column(Text, nullable=False)
    model_version      = Column(String, nullable=True)
    confidence         = Column(Float, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    status             = Column(String, default="new")  # new, under_review, escalated, resolved, dismissed_as_false_positive
    assigned_doctor_id = Column(String, ForeignKey("users.id"), nullable=True)
    review_timestamp   = Column(DateTime, nullable=True)
    doctor_notes       = Column(Text, nullable=True)
    resolution_reason  = Column(Text, nullable=True)

    # Relationships
    patient            = relationship("User", foreign_keys=[patient_id], back_populates="alerts")
    assigned_doctor    = relationship("User", foreign_keys=[assigned_doctor_id])


class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id        = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id  = Column(String, ForeignKey("users.id"), nullable=False)
    action    = Column(String, nullable=False)  # alert_opened, review_started, notes_added, alert_escalated, alert_resolved, alert_dismissed, doctor_patient_assignment_changed
    target_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    meta      = Column(JSON, default=dict)

    actor     = relationship("User")


class RAGDocument(Base):
    __tablename__ = "rag_documents"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename         = Column(String, nullable=False)
    title            = Column(String, nullable=False)
    version          = Column(String, default="1.0")
    file_hash        = Column(String, unique=True, index=True, nullable=False)
    is_active        = Column(JSON, default=True)  # handles active/inactive
    uploaded_at      = Column(DateTime, default=datetime.utcnow)
    ingestion_status = Column(String, default="processing")  # processing, success, failed
    metadata_json    = Column(JSON, default=dict)


class PatientInstruction(Base):
    __tablename__ = "patient_instructions"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id       = Column(String, ForeignKey("users.id"), nullable=False)
    patient_id      = Column(String, ForeignKey("users.id"), nullable=False)
    alert_id        = Column(String, ForeignKey("maternal_risk_alerts.id"), nullable=True)
    message         = Column(Text, nullable=False)
    priority        = Column(String, default="Normal")  # Normal, High
    created_at      = Column(DateTime, default=datetime.utcnow)
    patient_visible = Column(JSON, default=True)  # True if patient can read
    read_at         = Column(DateTime, nullable=True)
    expiry_date     = Column(DateTime, nullable=True)
    status          = Column(String, default="active")  # active, withdrawn

    # Relationships
    doctor          = relationship("User", foreign_keys=[doctor_id], back_populates="instructions_sent")
    patient         = relationship("User", foreign_keys=[patient_id], back_populates="instructions_received")
    alert           = relationship("MaternalRiskAlert")


class Appointment(Base):
    """Tracks patient appointments with their assigned doctor."""
    __tablename__ = "appointments"

    id                  = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id          = Column(String, ForeignKey("users.id"), nullable=False)
    doctor_id           = Column(String, ForeignKey("users.id"), nullable=False)
    appointment_datetime = Column(DateTime, nullable=False)
    appointment_type    = Column(String, nullable=False)        # e.g. 'checkup', 'emergency', 'follow_up', 'scan'
    reason              = Column(Text, nullable=False)
    status              = Column(String, default="requested")   # requested, confirmed, rescheduled, completed, cancelled, no_show
    doctor_notes        = Column(Text, nullable=True)
    patient_instructions = Column(Text, nullable=True)
    reschedule_reason   = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("User", foreign_keys=[patient_id])
    doctor  = relationship("User", foreign_keys=[doctor_id])


class MedicineReminder(Base):
    """Persistent medication reminders — doctor-prescribed or patient self-added."""
    __tablename__ = "medicine_reminders"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id      = Column(String, ForeignKey("users.id"), nullable=False)
    prescribed_by   = Column(String, ForeignKey("users.id"), nullable=True)   # None → self_added
    medicine_name   = Column(String, nullable=False)
    dosage          = Column(String, nullable=False)          # e.g. "500mg"
    frequency       = Column(String, nullable=False)          # e.g. "twice daily"
    reminder_times  = Column(JSON, default=list)              # ["08:00", "20:00"]
    start_date      = Column(DateTime, nullable=False)
    end_date        = Column(DateTime, nullable=True)
    instructions    = Column(Text, nullable=True)
    source          = Column(String, default="doctor")        # doctor | self_added
    is_active       = Column(JSON, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient     = relationship("User", foreign_keys=[patient_id])
    prescriber  = relationship("User", foreign_keys=[prescribed_by])
    adherences  = relationship("MedicineAdherence", back_populates="reminder", cascade="all, delete-orphan")


class MedicineAdherence(Base):
    """Records patient-reported dose status for each reminder slot."""
    __tablename__ = "medicine_adherences"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    reminder_id = Column(String, ForeignKey("medicine_reminders.id"), nullable=False)
    patient_id  = Column(String, ForeignKey("users.id"), nullable=False)
    dose_time   = Column(DateTime, nullable=False)
    status      = Column(String, nullable=False)   # taken | skipped | missed
    recorded_at = Column(DateTime, default=datetime.utcnow)
    notes       = Column(Text, nullable=True)

    reminder = relationship("MedicineReminder", back_populates="adherences")
    patient  = relationship("User", foreign_keys=[patient_id])


class Notification(Base):
    """Persistent in-app notifications for patients and doctors."""
    __tablename__ = "notifications"

    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = Column(String, ForeignKey("users.id"), nullable=False)
    notif_type    = Column(String, nullable=False)    # instruction | appointment | reminder | alert_review | follow_up
    message       = Column(Text, nullable=False)      # Safe, non-sensitive summary
    is_read       = Column(JSON, default=False)
    related_id    = Column(String, nullable=True)     # FK to relevant resource (appointment_id, reminder_id, etc.)
    related_type  = Column(String, nullable=True)     # 'appointment' | 'reminder' | 'instruction' | 'alert'
    expiry_date   = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])

