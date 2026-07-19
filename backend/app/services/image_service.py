import sys
import os
from PIL import Image
import logging

# Setup logging
logger = logging.getLogger("image-service")

# Add project root to path to allow importing from 'model'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    # Importing the new functional wrapper for the class-based classifier
    from model.predict import predict_image
    ML_SUPPORTED = True
except ImportError:
    logger.warning("ML prediction dependencies (torch/torchvision) not found. Falling back to basic analysis.")
    ML_SUPPORTED = False

def analyze_image(image_path: str) -> dict:
    """
    Service layer for image analysis. Integrates ML prediction and metadata extraction.
    """
    result = {
        "status": "success",
        "metadata": {
            "image_size": "Unknown",
            "format": "Unknown"
        },
        "ml_result": None
    }
    
    try:
        # 1. Metadata extraction
        with Image.open(image_path) as img:
            width, height = img.size
            result["metadata"]["image_size"] = f"{width}x{height}"
            result["metadata"]["format"] = img.format

        # 2. ML Prediction
        if ML_SUPPORTED:
            ml_prediction = predict_image(image_path)
            result["ml_result"] = ml_prediction
        else:
            result["ml_result"] = {
                "status": "unavailable",
                "message": "Model dependencies not installed on server."
            }

        return result
        
    except Exception as e:
        logger.error(f"Error processing image {image_path}: {e}")
        return {
            "status": "error",
            "message": f"Failed to process image: {str(e)}",
            "metadata": None,
            "ml_result": None
        }
