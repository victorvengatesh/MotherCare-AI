import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Float, JSON
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
