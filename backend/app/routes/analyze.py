from pathlib import Path
import shutil
import uuid
import logging
import magic
from PIL import Image, UnidentifiedImageError

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends

from app.services.symptom_service import analyze_symptoms
from app.services.image_service import analyze_image
from app.services.response_service import build_final_response
from app.services.history_service import check_similarity, add_to_history
from app.services.auth_service import get_current_user
from app.services.gemini_service import enhance_response
from app.db.database import get_db
from app.db import models
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger("mothercare-analyze")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE_MB = 5

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def validate_file(upload_file: UploadFile) -> None:
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file name received.",
        )

    extension = Path(upload_file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Please upload JPG, JPEG, PNG, or WEBP image.",
        )

@router.post("/analyze")
async def analyze(
    symptoms: str = Form(...),
    file: UploadFile | None = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not symptoms.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symptoms field cannot be empty.",
        )

    # 1. Preserve original text & run Multilingual NLP processing
    from app.services.normalization_service import process_multilingual_input
    nlp_res = process_multilingual_input(symptoms)
    
    lang = nlp_res["detected_language"]
    normalized_text = nlp_res["normalized_text"]
    extracted_symptoms = nlp_res["extracted_symptoms"]
    uncertain_terms = nlp_res["uncertain_terms"]
    requires_clinical_review = nlp_res["requires_clinical_review"]

    # 2. Run deterministic red-flag rules
    from app.services.redflag_service import screen_symptoms
    redflag_res = screen_symptoms(symptoms)
    
    # Emergency overrides
    critical_symptoms = ["bleeding", "reduced fetal movement", "difficulty breathing", "chest pain", "seizure", "blurry vision", "severe pain"]
    is_critical_extracted = any(s in extracted_symptoms for s in critical_symptoms)
    
    requires_immediate_care = redflag_res["requires_immediate_care"] or is_critical_extracted
    risk_level = "Emergency" if requires_immediate_care else redflag_res["risk_level"]
    detected_red_flags = redflag_res["detected_red_flags"]
    
    if is_critical_extracted and "Emergency" not in risk_level:
        risk_level = "Emergency"
        requires_immediate_care = True
        
    for s in extracted_symptoms:
        if s in critical_symptoms:
            label = s.replace("_", " ").title()
            if label not in detected_red_flags:
                detected_red_flags.append(label)

    # 3. Create persistent alerts when required
    if requires_immediate_care:
        from app.services.alert_service import create_maternal_alert
        create_maternal_alert(
            db=db,
            patient_id=current_user.id,
            risk_level=risk_level,
            alert_source="deterministic",
            warning_signs="; ".join(detected_red_flags)
        )

    # 4. Image Upload (ML prediction remains active)
    image_result = None
    meta = {"uploaded_file": None}

    if file and file.filename:
        validate_file(file)
        
        safe_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4().hex}{safe_extension}"
        saved_file_path = UPLOAD_DIR / unique_filename

        try:
            with saved_file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_size_mb = saved_file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File is too large. Maximum allowed size is {MAX_FILE_SIZE_MB} MB.",
                )

            mime_type = magic.from_file(str(saved_file_path), mime=True)
            if not mime_type.startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file content. Expected an image.",
                )
                
            try:
                with Image.open(saved_file_path) as img:
                    img.verify()
            except UnidentifiedImageError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Corrupted or invalid image file.",
                )

            logger.info("File saved successfully: %s", saved_file_path.name)
            image_result = analyze_image(str(saved_file_path))
            meta = {
                "uploaded_file": file.filename,
                "image_analysis": image_result,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error during analysis: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process the request.",
            )
        finally:
            await file.close()
            saved_file_path.unlink(missing_ok=True)

    # 5. Check Similarity
    history_note = None
    if check_similarity(db, current_user.id, symptoms):
        history_note = "You have reported similar symptoms before."

    # 6 & 7 & 8. RAG & Gemini Explanation with fallback protection
    rag_context = "insufficient approved information"
    citations = []
    final_explanation = "No detailed AI explanation is available at this moment. Please follow the recommended actions and consult a medical professional."
    if requires_immediate_care:
        final_explanation = "CRITICAL WARNING: Emergency signs detected. Please seek immediate professional medical attention at the nearest emergency department."

    try:
        from app.services.rag_service import get_relevant_context
        rag_context, citations = get_relevant_context(db, symptoms, current_user.id)

        from app.services.gemini_service import explain_with_rag, translate_response
        raw_explanation = explain_with_rag(symptoms, extracted_symptoms, risk_level, rag_context)
        final_explanation = translate_response(raw_explanation, lang)
    except Exception as e:
        logger.error("RAG or Gemini explanation pipeline failed: %s", e)

    if requires_immediate_care:
        if not final_explanation or "insufficient approved" in final_explanation.lower() or "no detailed ai explanation" in final_explanation.lower():
            final_explanation = "CRITICAL WARNING: Emergency signs detected. Please seek immediate professional medical attention at the nearest emergency department."

    # Save to SQL history log
    add_to_history(db, current_user.id, symptoms, {"condition": "; ".join(extracted_symptoms) if extracted_symptoms else "Unclear", "urgency": risk_level, "advice": final_explanation})

    # Prepare response payload
    reason = "Deterministic red-flags detected." if requires_immediate_care else "Standard screening analysis."
    recommended_action = "Seek immediate clinical care." if requires_immediate_care else "Standard care path. Monitor vitals."
    
    response_data = {
        "original_text": symptoms,
        "detected_language": lang,
        "normalized_text": normalized_text,
        "extracted_symptoms": extracted_symptoms,
        "uncertain_terms": uncertain_terms,
        "risk_level": risk_level,
        "detected_red_flags": detected_red_flags,
        "reason": reason,
        "recommended_action": recommended_action,
        "requires_immediate_care": requires_immediate_care,
        "requires_clinical_review": requires_clinical_review,
        "information_sources": citations,
        "response_language": lang,
        "explanation": final_explanation,
        "limitations": "This decision support relies strictly on available local clinical guidelines and text matching.",
        "disclaimer": "This is preliminary decision support, NOT clinical diagnosis. In emergencies, consult a qualified physician immediately.",
        "history_note": history_note,
        "meta": meta,
        # Backward compatibility with ResultCard.jsx:
        "condition": "; ".join(extracted_symptoms) if extracted_symptoms else "Unclear Symptoms",
        "urgency": risk_level,
        "advice": recommended_action,
        "gemini_response": final_explanation
    }

    from app.schemas.response import StandardResponse
    return StandardResponse(
        status="success",
        data=response_data,
        message="Analysis completed"
    )