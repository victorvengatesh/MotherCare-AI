import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.services.alert_service import create_audit_event
from app.schemas.response import StandardResponse

router = APIRouter(prefix="/admin")

def get_current_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    return current_user

class AssignRequest(BaseModel):
    doctor_id: str
    patient_id: str

class UnassignRequest(BaseModel):
    doctor_id: str
    patient_id: str

@router.post("/assign", response_model=StandardResponse[dict])
def assign_patient(
    body: AssignRequest,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # Verify doctor and patient exist and have correct roles
    doctor = db.query(models.User).filter(models.User.id == body.doctor_id).first()
    patient = db.query(models.User).filter(models.User.id == body.patient_id).first()
    
    if not doctor or doctor.role != "doctor":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or user is not a doctor")
    if not patient or patient.role != "patient":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or user is not a patient")
        
    # Check if assignment already exists
    existing = db.query(models.DoctorPatientAssignment).filter(
        models.DoctorPatientAssignment.doctor_id == body.doctor_id,
        models.DoctorPatientAssignment.patient_id == body.patient_id
    ).first()
    
    if existing:
        if existing.status == "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment already active")
        else:
            # Reactivate
            existing.status = "active"
            existing.assigned_date = datetime.utcnow()
            existing.assigned_by = current_admin.username
            existing.end_date = None
            assignment = existing
    else:
        assignment = models.DoctorPatientAssignment(
            doctor_id=body.doctor_id,
            patient_id=body.patient_id,
            status="active",
            assigned_by=current_admin.username
        )
        db.add(assignment)
        
    try:
        db.commit()
        db.refresh(assignment)
        
        # Log audit trail
        create_audit_event(
            db=db,
            actor_id=current_admin.id,
            action="doctor_patient_assignment_changed",
            target_id=assignment.id,
            meta={"doctor_id": body.doctor_id, "patient_id": body.patient_id, "status": "active"}
        )
        
        return StandardResponse(
            status="success",
            message="Patient successfully assigned to doctor",
            data={"assignment_id": assignment.id}
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/unassign", response_model=StandardResponse[dict])
def unassign_patient(
    body: UnassignRequest,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    assignment = db.query(models.DoctorPatientAssignment).filter(
        models.DoctorPatientAssignment.doctor_id == body.doctor_id,
        models.DoctorPatientAssignment.patient_id == body.patient_id,
        models.DoctorPatientAssignment.status == "active"
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active assignment not found")
        
    assignment.status = "inactive"
    assignment.end_date = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(assignment)
        
        # Log audit trail
        create_audit_event(
            db=db,
            actor_id=current_admin.id,
            action="doctor_patient_assignment_changed",
            target_id=assignment.id,
            meta={"doctor_id": body.doctor_id, "patient_id": body.patient_id, "status": "inactive"}
        )
        
        return StandardResponse(
            status="success",
            message="Patient successfully unassigned from doctor",
            data={"assignment_id": assignment.id}
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/assignments", response_model=StandardResponse[dict])
def get_assignments(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    assignments = db.query(models.DoctorPatientAssignment).all()
    res = []
    for a in assignments:
        doctor = db.query(models.User).filter(models.User.id == a.doctor_id).first()
        patient = db.query(models.User).filter(models.User.id == a.patient_id).first()
        res.append({
            "id": a.id,
            "doctor": {"id": doctor.id, "username": doctor.username} if doctor else None,
            "patient": {"id": patient.id, "username": patient.username} if patient else None,
            "status": a.status,
            "assigned_date": a.assigned_date.isoformat() if a.assigned_date else None,
            "assigned_by": a.assigned_by,
            "end_date": a.end_date.isoformat() if a.end_date else None
        })
    return StandardResponse(status="success", data={"assignments": res})

@router.get("/users", response_model=StandardResponse[dict])
def get_users(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    users = db.query(models.User).all()
    res = []
    for u in users:
        res.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role
        })
    return StandardResponse(status="success", data={"users": res})


# ── RAG Guideline Administration Endpoints ─────────────────────────────────────
import shutil
import hashlib
from pathlib import Path
from fastapi import UploadFile, File, Form
from app.services.rag_service import (
    validate_guideline_pdf, 
    index_medical_document_page_by_page, 
    delete_medical_chunks
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/rag/upload", response_model=StandardResponse[dict])
async def upload_guideline_pdf(
    title: str = Form(...),
    version: str = Form("1.0"),
    file: UploadFile = File(...),
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # 1. Save upload file to temporary location
    temp_filename = f"temp_{uuid.uuid4().hex}_{file.filename}"
    temp_path = UPLOAD_DIR / temp_filename
    
    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Perform validations
        is_valid, err_msg = validate_guideline_pdf(temp_path)
        if not is_valid:
            temp_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=err_msg)
            
        # 3. Compute file hash to prevent duplicate document ingestion
        hasher = hashlib.sha256()
        with temp_path.open("rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        file_hash = hasher.hexdigest()
        
        existing = db.query(models.RAGDocument).filter_by(file_hash=file_hash).first()
        if existing:
            temp_path.unlink(missing_ok=True)
            if existing.ingestion_status == "success":
                raise HTTPException(status_code=400, detail="Document with identical hash already exists and is successfully indexed.")
            else:
                # Allow re-attempting failed/processing ones
                db.delete(existing)
                db.commit()

        # 4. Create database entry
        doc_record = models.RAGDocument(
            filename=file.filename,
            title=title,
            version=version,
            file_hash=file_hash,
            is_active=True,
            ingestion_status="processing"
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)
        
        # 5. Extract and index chunks page-by-page
        try:
            chunks_count = index_medical_document_page_by_page(
                temp_path, doc_record.id, title, version
            )
            doc_record.ingestion_status = "success" if chunks_count > 0 else "failed"
            doc_record.metadata_json = {"chunks_count": chunks_count}
            db.commit()
        except Exception as e:
            doc_record.ingestion_status = "failed"
            doc_record.metadata_json = {"error": str(e)}
            db.commit()
            raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")
            
        # 6. Log audit trail
        create_audit_event(
            db=db,
            actor_id=current_admin.id,
            action="rag_document_uploaded",
            target_id=doc_record.id,
            meta={"title": title, "version": version, "chunks_count": chunks_count if 'chunks_count' in locals() else 0}
        )
        
        return StandardResponse(
            status="success",
            message="Document successfully uploaded and indexed.",
            data={"document_id": doc_record.id, "chunks": doc_record.metadata_json.get("chunks_count")}
        )
    finally:
        temp_path.unlink(missing_ok=True)


@router.get("/rag/documents", response_model=StandardResponse[dict])
def list_guidelines(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    docs = db.query(models.RAGDocument).order_by(models.RAGDocument.uploaded_at.desc()).all()
    res = []
    for d in docs:
        res.append({
            "id": d.id,
            "filename": d.filename,
            "title": d.title,
            "version": d.version,
            "is_active": d.is_active,
            "uploaded_at": d.uploaded_at.isoformat(),
            "ingestion_status": d.ingestion_status,
            "metadata": d.metadata_json
        })
    return StandardResponse(status="success", data={"documents": res})


@router.get("/rag/document/{doc_id}", response_model=StandardResponse[dict])
def get_guideline(
    doc_id: str,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    doc = db.query(models.RAGDocument).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return StandardResponse(status="success", data={
        "id": doc.id,
        "filename": doc.filename,
        "title": doc.title,
        "version": doc.version,
        "is_active": doc.is_active,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "ingestion_status": doc.ingestion_status,
        "metadata": doc.metadata_json
    })


@router.put("/rag/document/{doc_id}/toggle", response_model=StandardResponse[dict])
def toggle_guideline(
    doc_id: str,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    doc = db.query(models.RAGDocument).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc.is_active = not doc.is_active
    db.commit()
    
    create_audit_event(
        db=db,
        actor_id=current_admin.id,
        action="rag_document_toggled",
        target_id=doc.id,
        meta={"is_active": doc.is_active}
    )
    
    return StandardResponse(
        status="success", 
        message=f"Document set to {'active' if doc.is_active else 'inactive'}",
        data={"is_active": doc.is_active}
    )


@router.delete("/rag/document/{doc_id}", response_model=StandardResponse[dict])
def delete_guideline(
    doc_id: str,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    doc = db.query(models.RAGDocument).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Remove from vector db chunks
    delete_medical_chunks(doc.id)
    
    db.delete(doc)
    db.commit()
    
    create_audit_event(
        db=db,
        actor_id=current_admin.id,
        action="rag_document_deleted",
        target_id=doc_id
    )
    
    return StandardResponse(status="success", message="Document deleted successfully from SQL and vector stores.")


@router.get("/rag/document/{doc_id}/status", response_model=StandardResponse[dict])
def get_guideline_status(
    doc_id: str,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    doc = db.query(models.RAGDocument).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return StandardResponse(status="success", data={"id": doc.id, "ingestion_status": doc.ingestion_status})

