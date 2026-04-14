from pathlib import Path
import shutil
import uuid
import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status

from app.services.symptom_service import analyze_symptoms
from app.services.image_service import analyze_image
from app.services.response_service import build_final_response
from app.services.history_service import check_similarity, add_to_history

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
):
    if not symptoms.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symptoms field cannot be empty.",
        )

    symptom_result = analyze_symptoms(symptoms)
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
                saved_file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File is too large. Maximum allowed size is {MAX_FILE_SIZE_MB} MB.",
                )

            logger.info("File saved successfully: %s", saved_file_path.name)
            image_result = analyze_image(str(saved_file_path))
            meta = {
                "uploaded_file": file.filename,
                "stored_file": unique_filename,
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

    history_note = None
    if check_similarity(symptoms):
        history_note = "You have reported similar symptoms before."

    response = build_final_response(
        symptom_result=symptom_result,
        image_result=image_result,
        history_note=history_note
    )

    # Save current query to history
    add_to_history(symptoms, symptom_result)

    return {
        "status": "success",
        "data": response,
        "meta": meta,
    }