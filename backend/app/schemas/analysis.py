from pydantic import BaseModel
from typing import Optional

class AnalysisResponse(BaseModel):
    """Schema for the preliminary analysis response"""
    condition: str
    urgency: str
    advice: str
    disclaimer: str

class AnalysisRequestMetadata(BaseModel):
    """Schema for metadata if needed in future versions"""
    user_id: Optional[str] = None
    timestamp: Optional[str] = None
