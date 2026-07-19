import json
from pathlib import Path
import logging

logger = logging.getLogger("response-service")

# Path configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
KNOWLEDGE_DIR = BASE_DIR / "data" / "medical_knowledge"

def load_json(filename):
    path = KNOWLEDGE_DIR / filename
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load knowledge file {filename}: {e}")
        return {}

def build_final_response(symptom_result: dict, image_result: dict | None, history_note: str = None) -> dict:
    """
    Aggregates symptom analysis, image analysis, and history into a cohesive response.
    Uses structured knowledge for refinement.
    """
    # 1. Base response from symptoms
    condition = symptom_result.get("condition", "Unclear condition requiring evaluation")
    urgency = symptom_result.get("urgency", "Moderate")
    advice = symptom_result.get("advice", "Please consult a healthcare professional.")

    # 2. Enrich with Image Analysis if available
    if image_result and image_result.get("ml_result"):
        ml_res = image_result["ml_result"]
        
        if ml_res.get("status") == "success" and ml_res.get("interpretation") == "confident":
            predicted_class = ml_res["predicted_class"]
            
            # Load image group mapping
            image_class_groups = load_json("image_class_groups.json")
            disease_groups = load_json("disease_groups.json")
            advice_templates = load_json("advice_templates.json")
            
            group_id = image_class_groups.get(predicted_class)
            if group_id:
                group_info = disease_groups.get(group_id)
                if group_info:
                    # Refine condition label if it differs from symptom group
                    if symptom_result.get("internal_group") != group_id:
                        condition = f"{condition} (Physical check suggests {group_info['label']})"
                    
                    # Add image-specific advice if available
                    group_advice = advice_templates.get(group_id, {})
                    refined_advice = group_advice.get(urgency) or list(group_advice.values())[0]
                    
                    if refined_advice:
                        advice = f"{advice} For immediate care: {refined_advice}"

    response = {
        "condition": condition,
        "urgency": urgency,
        "advice": advice,
        "disclaimer": "This system provides preliminary guidance only and is not a substitute for professional medical advice."
    }
    
    if history_note:
        response["history_note"] = history_note
        
    return response

