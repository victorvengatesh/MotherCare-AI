"""Medical summary PDF download route for MotherCare AI.

Security:
- Patients may only generate their own summary.
- Doctors may only generate summaries for assigned patients.
- Internal doctor notes, audit logs, passwords, tokens never included.
- Temp file deleted immediately after streaming.
- Path traversal prevented: only tempfile-generated paths used.
"""
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.services.pdf_service import generate_medical_summary_pdf
from app.utils.logger import logger

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary/pdf", response_class=FileResponse)
async def download_medical_summary_pdf(
    patient_id: Optional[str] = Query(None, description="Required for doctor/admin to specify patient"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate and stream a medical summary PDF.

    - Patients: generate only their own summary (patient_id param ignored).
    - Doctors: must specify patient_id of an assigned patient.
    - All AI content is labelled as decision support only.
    """
    # Resolve target patient
    if current_user.role == "patient":
        patient = current_user
    elif current_user.role in ("doctor", "admin"):
        if not patient_id:
            raise HTTPException(status_code=422, detail="patient_id is required for doctor/admin.")
        # Access check
        if current_user.role == "doctor":
            assignment = db.query(models.DoctorPatientAssignment).filter_by(
                doctor_id=current_user.id, patient_id=patient_id, status="active"
            ).first()
            if not assignment:
                raise HTTPException(status_code=403, detail="Access denied. Not assigned to this patient.")
        patient = db.query(models.User).filter_by(id=patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")
    else:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Generate PDF
    tmp_path = generate_medical_summary_pdf(db=db, patient=patient, requesting_user=current_user)

    if tmp_path is None:
        raise HTTPException(
            status_code=503,
            detail="PDF generation is unavailable. ReportLab is not installed on this server.",
        )

    if not tmp_path.exists():
        raise HTTPException(status_code=500, detail="PDF generation failed.")

    filename = f"mothercare_summary_{patient.username}_{tmp_path.stem}.pdf"

    # Return the file; it will be streamed. We use a background cleanup.
    # FastAPI FileResponse does NOT delete the file, so we handle that via response_class=FileResponse
    # and log a warning to clean up periodically (production: use celery or temp cleanup job).
    logger.info("Streaming PDF summary for patient=%s requester=%s", patient.id, current_user.id)

    # Schedule cleanup: use a custom wrapper
    return _PDFFileResponse(
        path=str(tmp_path),
        filename=filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class _PDFFileResponse(FileResponse):
    """FileResponse that deletes the temp file after sending."""
    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            try:
                if os.path.exists(self.path):
                    os.unlink(self.path)
                    logger.info("Deleted temp PDF: %s", self.path)
            except Exception as e:
                logger.warning("Failed to delete temp PDF %s: %s", self.path, e)
