import sys
import os
from PIL import Image

# Add project root to path to allow importing from 'model'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from model.predict import predict_image
    ML_SUPPORTED = True
except ImportError:
    print("Warning: ML prediction dependencies (torch/torchvision) not found. Falling back to basic analysis.")
    ML_SUPPORTED = False

def analyze_image(image_path: str) -> dict:
    result = {
        "image_status": "Image received successfully",
        "image_size": "Unknown",
        "ml_analysis": None
    }
    
    try:
        # Basic Image Analysis
        img = Image.open(image_path)
        width, height = img.size
        result["image_size"] = f"{width}x{height}"

        # ML Prediction
        if ML_SUPPORTED:
            ml_result = predict_image(image_path)
            result["ml_analysis"] = ml_result
        else:
            result["ml_analysis"] = {
                "status": "unavailable",
                "message": "Model dependencies not installed on server."
            }

        return result
        
    except Exception as e:
        return {
            "image_status": f"Error processing image: {str(e)}",
            "image_size": "Unknown",
            "ml_analysis": None
        }
