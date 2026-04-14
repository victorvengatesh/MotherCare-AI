def build_final_response(symptom_result: dict, image_result: dict, history_note: str = None) -> dict:
    response = {
        "condition": symptom_result.get("condition", "Unclear skin-related condition"),
        "urgency": symptom_result.get("urgency", "Unknown"),
        "advice": symptom_result.get(
            "advice",
            "Please consult a healthcare professional for a proper evaluation."
        ),
        "disclaimer": "This system provides preliminary guidance only and is not a substitute for professional medical advice."
    }
    
    if history_note:
        response["history_note"] = history_note
        
    return response
