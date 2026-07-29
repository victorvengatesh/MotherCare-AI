import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.services.symptom_service import analyze_symptoms
from app.services.response_service import build_final_response

import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_case(name, symptoms, image_result=None):
    print(f"\n--- Test Case: {name} ---")
    try:
        print(f"Input: {symptoms}")
    except UnicodeEncodeError:
        print(f"Input: [Contains Unicode characters]")

    symptom_res = analyze_symptoms(symptoms)
    final_res = build_final_response(symptom_res, image_result)
    
    print(f"Condition: {final_res['condition']}")
    print(f"Urgency: {final_res['urgency']}")
    print(f"Advice: {final_res['advice'][:100]}...")
    print(f"Internal Path: {symptom_res.get('internal_group')} | Symptoms: {symptom_res.get('detected_symptoms')}")

if __name__ == "__main__":
    # Test cases requested by the user
    test_case("Case 1 (Typo + Duration)", "i have feaver in two two days")
    test_case("Case 2 (Standard Duration)", "i have fever for two days")
    test_case("Case 3 (Tamil Duration)", "காய்ச்சல் இரு நாள்")
    test_case("Case 4 (Typo + Mixed)", "feaver and body pain")
    test_case("Case 5 (Typo + Weakness)", "high feaver and weakness")
    
    # Existing integration test
    mock_burn_image = {
        "ml_result": {
            "status": "success",
            "interpretation": "confident",
            "predicted_class": "burn"
        }
    }
    test_case("Image Integration", "My hand is red and has a blister", mock_burn_image)

