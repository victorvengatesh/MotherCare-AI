"""
Email Service for MotherCare AI — Phase 4

Sends async HTML emails via SMTP (aiosmtplib).
Gracefully skips sending if SMTP is not configured (non-blocking).

Configuration (environment variables):
  SMTP_HOST      — SMTP server host  (e.g. smtp.gmail.com)
  SMTP_PORT      — SMTP port         (default: 587)
  SMTP_USER      — SMTP username / email address
  SMTP_PASS      — SMTP password / app password
  FROM_EMAIL     — Sender address    (default: SMTP_USER)
  FROM_NAME      — Sender display name (default: MotherCare AI)
"""

import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASS"))


def _smtp_config() -> dict:
    return {
        "hostname": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASS", ""),
        "from_email": os.getenv("FROM_EMAIL") or os.getenv("SMTP_USER", ""),
        "from_name": os.getenv("FROM_NAME", "MotherCare AI"),
    }


# ---------------------------------------------------------------------------
# Base send function
# ---------------------------------------------------------------------------

async def send_email(
    to: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> bool:
    """
    Send a single email asynchronously.

    Returns True on success, False on failure.
    If SMTP is not configured, logs a warning and returns False silently.
    """
    if not _smtp_configured():
        logger.debug("SMTP not configured — skipping email to %s", to)
        return False

    cfg = _smtp_config()

    try:
        import aiosmtplib

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{cfg['from_name']} <{cfg['from_email']}>"
        msg["To"] = to

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=cfg["hostname"],
            port=cfg["port"],
            username=cfg["username"],
            password=cfg["password"],
            start_tls=True,
        )

        logger.info("Email sent to %s: %s", to, subject)
        return True

    except Exception as e:
        logger.warning("Failed to send email to %s: %s", to, e)
        return False


# ---------------------------------------------------------------------------
# Branded HTML template helper
# ---------------------------------------------------------------------------

def _html_template(title: str, content: str) -> str:
    """Wrap content in a branded MotherCare AI HTML email template."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 580px; margin: 32px auto; background: #ffffff;
                border-radius: 12px; overflow: hidden;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
    .header {{ background: linear-gradient(135deg, #e91e8c, #9c27b0);
               padding: 28px 32px; text-align: center; }}
    .header h1 {{ color: #ffffff; margin: 0; font-size: 22px; font-weight: 700; }}
    .header p  {{ color: rgba(255,255,255,0.85); margin: 6px 0 0; font-size: 13px; }}
    .body {{ padding: 32px; color: #2d3748; line-height: 1.7; }}
    .body h2 {{ color: #1a202c; font-size: 18px; margin: 0 0 16px; }}
    .body p  {{ margin: 0 0 14px; font-size: 15px; }}
    .info-box {{ background: #f7fafc; border-left: 4px solid #e91e8c;
                 border-radius: 6px; padding: 16px 20px; margin: 20px 0; }}
    .info-box p {{ margin: 6px 0; font-size: 14px; }}
    .info-box strong {{ color: #e91e8c; }}
    .alert-box {{ background: #fff5f5; border-left: 4px solid #e53e3e;
                  border-radius: 6px; padding: 16px 20px; margin: 20px 0; }}
    .alert-box p {{ margin: 6px 0; font-size: 14px; color: #c53030; }}
    .footer {{ background: #f7fafc; padding: 20px 32px; text-align: center;
               border-top: 1px solid #e2e8f0; }}
    .footer p {{ color: #718096; font-size: 12px; margin: 4px 0; }}
    .disclaimer {{ font-size: 11px; color: #a0aec0; margin-top: 8px; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>🌸 MotherCare AI</h1>
      <p>Bilingual Maternal Healthcare Support</p>
    </div>
    <div class="body">
      {content}
    </div>
    <div class="footer">
      <p>MotherCare AI — Preliminary Healthcare Guidance</p>
      <p class="disclaimer">
        This is an automated message. Do not reply to this email.<br>
        MotherCare AI provides preliminary guidance only — always consult a qualified healthcare professional.
      </p>
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Appointment emails
# ---------------------------------------------------------------------------

async def send_appointment_confirmation(
    patient_email: str,
    patient_name: str,
    doctor_name: str,
    appointment_datetime: str,
    appointment_type: str,
    reason: str,
) -> bool:
    """Send appointment confirmation email to patient."""
    subject = "✅ Appointment Confirmed — MotherCare AI"
    body_text = (
        f"Dear {patient_name},\n\n"
        f"Your {appointment_type} appointment with Dr. {doctor_name} has been confirmed.\n"
        f"Date & Time: {appointment_datetime}\n"
        f"Reason: {reason}\n\n"
        "Please arrive 10 minutes early.\n\n"
        "MotherCare AI"
    )
    content = f"""
        <h2>Appointment Confirmed ✅</h2>
        <p>Dear <strong>{patient_name}</strong>,</p>
        <p>Your appointment has been confirmed. Here are the details:</p>
        <div class="info-box">
          <p><strong>Type:</strong> {appointment_type.replace('_', ' ').title()}</p>
          <p><strong>Doctor:</strong> Dr. {doctor_name}</p>
          <p><strong>Date & Time:</strong> {appointment_datetime}</p>
          <p><strong>Reason:</strong> {reason}</p>
        </div>
        <p>Please arrive <strong>10 minutes early</strong> and bring any relevant health documents.</p>
    """
    return await send_email(patient_email, subject, body_text, _html_template(subject, content))


async def send_appointment_rescheduled(
    patient_email: str,
    patient_name: str,
    doctor_name: str,
    new_datetime: str,
    reschedule_reason: str,
) -> bool:
    """Notify patient that appointment was rescheduled."""
    subject = "📅 Appointment Rescheduled — MotherCare AI"
    body_text = (
        f"Dear {patient_name},\n\n"
        f"Your appointment with Dr. {doctor_name} has been rescheduled.\n"
        f"New Date & Time: {new_datetime}\n"
        f"Reason: {reschedule_reason}\n\n"
        "MotherCare AI"
    )
    content = f"""
        <h2>Appointment Rescheduled 📅</h2>
        <p>Dear <strong>{patient_name}</strong>,</p>
        <p>Your appointment with Dr. <strong>{doctor_name}</strong> has been rescheduled.</p>
        <div class="info-box">
          <p><strong>New Date & Time:</strong> {new_datetime}</p>
          <p><strong>Reason for rescheduling:</strong> {reschedule_reason}</p>
        </div>
        <p>If you have any questions, please contact your care team.</p>
    """
    return await send_email(patient_email, subject, body_text, _html_template(subject, content))


async def send_appointment_cancelled(
    patient_email: str,
    patient_name: str,
    doctor_name: str,
    cancellation_reason: str,
) -> bool:
    """Notify patient that appointment was cancelled."""
    subject = "❌ Appointment Cancelled — MotherCare AI"
    body_text = (
        f"Dear {patient_name},\n\n"
        f"Your appointment with Dr. {doctor_name} has been cancelled.\n"
        f"Reason: {cancellation_reason}\n\n"
        "Please log in to MotherCare AI to schedule a new appointment.\n\n"
        "MotherCare AI"
    )
    content = f"""
        <h2>Appointment Cancelled ❌</h2>
        <p>Dear <strong>{patient_name}</strong>,</p>
        <p>Your appointment with Dr. <strong>{doctor_name}</strong> has been cancelled.</p>
        <div class="info-box">
          <p><strong>Cancellation reason:</strong> {cancellation_reason}</p>
        </div>
        <p>Please log in to MotherCare AI to request a new appointment at your convenience.</p>
    """
    return await send_email(patient_email, subject, body_text, _html_template(subject, content))


# ---------------------------------------------------------------------------
# Alert emails (doctor notifications)
# ---------------------------------------------------------------------------

async def send_high_risk_alert_to_doctor(
    doctor_email: str,
    doctor_name: str,
    patient_name: str,
    risk_level: str,
    warning_signs: str,
    alert_source: str,
) -> bool:
    """Email the assigned doctor when a HIGH or EMERGENCY risk alert is created."""
    subject = f"🚨 {risk_level} Risk Alert — Patient: {patient_name}"
    body_text = (
        f"Dear Dr. {doctor_name},\n\n"
        f"A {risk_level} risk alert has been raised for your patient {patient_name}.\n"
        f"Source: {alert_source}\n"
        f"Warning signs: {warning_signs}\n\n"
        "Please log in to MotherCare AI to review and take action.\n\n"
        "MotherCare AI Clinical Alert System"
    )
    box_class = "alert-box" if risk_level == "Emergency" else "info-box"
    content = f"""
        <h2>{'🚨' if risk_level == 'Emergency' else '⚠️'} {risk_level} Risk Alert</h2>
        <p>Dear Dr. <strong>{doctor_name}</strong>,</p>
        <p>A <strong>{risk_level}</strong> risk alert has been raised for one of your patients.</p>
        <div class="{box_class}">
          <p><strong>Patient:</strong> {patient_name}</p>
          <p><strong>Alert source:</strong> {alert_source.replace('_', ' ').title()}</p>
          <p><strong>Warning signs:</strong> {warning_signs}</p>
        </div>
        <p>Please <strong>log in to MotherCare AI immediately</strong> to review this alert and take appropriate action.</p>
    """
    return await send_email(doctor_email, subject, body_text, _html_template(subject, content))


# ---------------------------------------------------------------------------
# Medicine reminder email
# ---------------------------------------------------------------------------

async def send_medicine_reminder_email(
    patient_email: str,
    patient_name: str,
    medicine_name: str,
    dosage: str,
    frequency: str,
    instructions: Optional[str] = None,
) -> bool:
    """Notify patient about a new medicine reminder prescribed by their doctor."""
    subject = "💊 New Medicine Reminder — MotherCare AI"
    body_text = (
        f"Dear {patient_name},\n\n"
        f"Your doctor has added a medicine reminder for you.\n"
        f"Medicine: {medicine_name}\n"
        f"Dosage: {dosage}\n"
        f"Frequency: {frequency}\n"
        + (f"Instructions: {instructions}\n" if instructions else "")
        + "\nPlease log in to MotherCare AI to view and track your medication.\n\n"
        "MotherCare AI"
    )
    content = f"""
        <h2>New Medicine Reminder 💊</h2>
        <p>Dear <strong>{patient_name}</strong>,</p>
        <p>Your doctor has added a new medicine reminder to your care plan.</p>
        <div class="info-box">
          <p><strong>Medicine:</strong> {medicine_name}</p>
          <p><strong>Dosage:</strong> {dosage}</p>
          <p><strong>Frequency:</strong> {frequency}</p>
          {f"<p><strong>Instructions:</strong> {instructions}</p>" if instructions else ""}
        </div>
        <p>Log in to MotherCare AI to track your medication adherence.</p>
    """
    return await send_email(patient_email, subject, body_text, _html_template(subject, content))
