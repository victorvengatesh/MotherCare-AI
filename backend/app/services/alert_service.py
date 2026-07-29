import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.db import models
from app.services.redflag_service import screen_symptoms

logger = logging.getLogger("alert-service")

def create_maternal_alert(
    db: Session,
    patient_id: str,
    risk_level: str,
    alert_source: str,
    warning_signs: str,
    confidence: float = None,
    model_version: str = "v1.0.0-rf"
) -> models.MaternalRiskAlert | None:
    """
    Creates a persistent maternal risk alert. If an active alert (status is new or under_review)
    for the same patient and source exists, we update it instead of creating a duplicate.
    """
    # Find active doctor assignment for this patient to assign the alert automatically
    assignment = (
        db.query(models.DoctorPatientAssignment)
        .filter(
            models.DoctorPatientAssignment.patient_id == patient_id,
            models.DoctorPatientAssignment.status == "active"
        )
        .first()
    )
    assigned_doctor_id = assignment.doctor_id if assignment else None

    # Check for existing active alert for this source and patient
    existing_alert = (
        db.query(models.MaternalRiskAlert)
        .filter(
            models.MaternalRiskAlert.patient_id == patient_id,
            models.MaternalRiskAlert.alert_source == alert_source,
            models.MaternalRiskAlert.status.in_(["new", "under_review"])
        )
        .first()
    )

    if existing_alert:
        # Update existing alert
        existing_alert.risk_level = risk_level
        existing_alert.warning_signs = warning_signs
        existing_alert.confidence = confidence
        existing_alert.model_version = model_version
        if assigned_doctor_id and not existing_alert.assigned_doctor_id:
            existing_alert.assigned_doctor_id = assigned_doctor_id
        db.commit()
        db.refresh(existing_alert)
        logger.info("Updated existing active alert for user %s: ID %s", patient_id, existing_alert.id)
        return existing_alert

    # Create new alert
    new_alert = models.MaternalRiskAlert(
        patient_id=patient_id,
        risk_level=risk_level,
        alert_source=alert_source,
        warning_signs=warning_signs,
        confidence=confidence,
        model_version=model_version,
        status="new",
        assigned_doctor_id=assigned_doctor_id
    )

    try:
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        
        # Log audit trail
        create_audit_event(
            db=db,
            actor_id=patient_id,  # System-generated on behalf of patient state
            action="alert_created",
            target_id=new_alert.id,
            meta={"alert_source": alert_source, "risk_level": risk_level}
        )
        
        logger.info("Created new alert for user %s: ID %s", patient_id, new_alert.id)
        return new_alert
    except Exception as e:
        db.rollback()
        logger.exception("Failed to save alert to database: %s", e)
        return None

def create_audit_event(
    db: Session,
    actor_id: str,
    action: str,
    target_id: str,
    meta: dict = None
) -> models.AuditTrail | None:
    """
    Creates an audit event in the database for tracking critical operations.
    """
    event = models.AuditTrail(
        actor_id=actor_id,
        action=action,
        target_id=target_id,
        meta=meta or {}
    )
    try:
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception as e:
        db.rollback()
        logger.exception("Failed to write audit event: %s", e)
        return None

def process_symptom_alert(db: Session, patient_id: str, symptoms: str):
    """
    Runs deterministic screening and creates an emergency alert if critical symptoms are found.
    """
    if not symptoms:
        return
    res = screen_symptoms(symptoms)
    if res.get("requires_immediate_care"):
        create_maternal_alert(
            db=db,
            patient_id=patient_id,
            risk_level="Emergency",
            alert_source="deterministic",
            warning_signs=", ".join(res.get("detected_red_flags", []))
        )

def process_twin_alerts(db: Session, patient_id: str, twin_data: dict, risks: dict):
    """
    Analyzes digital twin vitals and risk scores to raise alerts.
    """
    # 1. Vitals Safety Threshold Checks
    bp_sys = float(twin_data.get("systolic_bp", 120))
    bp_dia = float(twin_data.get("diastolic_bp", 80))
    glucose = float(twin_data.get("glucose_level", 90))
    hb = float(twin_data.get("hemoglobin", 12))
    hr = float(twin_data.get("heart_rate", 75))
    temp = float(twin_data.get("body_temp", 98.6))

    vitals_warnings = []
    if bp_sys >= 140 or bp_dia >= 90:
        vitals_warnings.append(f"Hypertension (BP {bp_sys}/{bp_dia})")
    if glucose >= 140:
        vitals_warnings.append(f"Hyperglycemia (Glucose {glucose} mg/dL)")
    if hb < 11.0:
        vitals_warnings.append(f"Low Hemoglobin ({hb} g/dL)")
    if hr >= 100 or hr <= 50:
        vitals_warnings.append(f"Abnormal Heart Rate ({hr} bpm)")
    if temp >= 100.4:
        vitals_warnings.append(f"High Fever ({temp}°F)")
    elif temp <= 96.0:
        vitals_warnings.append(f"Hypothermia ({temp}°F)")

    if vitals_warnings:
        create_maternal_alert(
            db=db,
            patient_id=patient_id,
            risk_level="High" if any("Hypertension" in w or "Fever" in w for w in vitals_warnings) else "Moderate",
            alert_source="vitals",
            warning_signs="; ".join(vitals_warnings)
        )

    # 2. ML Risk Checks
    # Risks has {"risk_scores": {"pre_eclampsia": p1, "gestational_diabetes": p2, "anemia": p3}, "overall_risk": str}
    scores = risks.get("risk_scores", {})
    high_ml_risks = []
    low_confidence_risks = []

    for name, p in scores.items():
        # Confidence score for binary prediction
        confidence = max(p, 1.0 - p)
        
        # If overall score >= 0.7, it's high risk
        if p >= 0.7:
            high_ml_risks.append(f"High Risk of {name.replace('_', ' ').title()} ({int(p*100)}%)")
        
        # If confidence is low (< 0.6) and risk is borderline (e.g. probability 0.4 to 0.6)
        if confidence < 0.6:
            low_confidence_risks.append(f"Borderline {name.replace('_', ' ').title()} ({int(p*100)}% risk, confidence {int(confidence*100)}%)")

    # Raise High Risk ML Alert
    if high_ml_risks:
        create_maternal_alert(
            db=db,
            patient_id=patient_id,
            risk_level="High",
            alert_source="ml",
            warning_signs="; ".join(high_ml_risks),
            confidence=min(scores.values()) # use the min probability as confidence marker
        )

    # Raise Low Confidence Clinical Review Alert
    if low_confidence_risks:
        create_maternal_alert(
            db=db,
            patient_id=patient_id,
            risk_level="Moderate",
            alert_source="ml",
            warning_signs="Clinical Review Required (Low Confidence): " + "; ".join(low_confidence_risks),
            confidence=0.55 # mock low confidence
        )
