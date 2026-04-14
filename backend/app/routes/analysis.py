from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.schemas.analysis import AnalysisResponse
from app.services.analysis_service import perform_comprehensive_analysis

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_symptoms(
    symptoms: str = Form(...),
    image: UploadFile = File(None)
):
    """
    Endpoint to analyze text symptoms and an optional image.
    Receives form data (symptoms as text and image as a file).
    """
    try:
        # Pass the data to the service layer for processing
        result = await perform_comprehensive_analysis(symptoms, image)
        return result
    except Exception as e:
        # In a real app, errors would be logged and more specific
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
