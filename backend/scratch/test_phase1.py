import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import logging
logging.basicConfig(level=logging.INFO)

from app.services.symptom_service import analyze_symptoms

def test_engine():
    tests = [
        {
            "name": "Typo Handling (English)",
            "input": "I have a fevvrr and coughh",
            "expected_symptom": "fever"
        },
        {
            "name": "Tamil Colloquial Parsing",
            "input": "வயித்து வலிக்குது", # 'vayi vali' variations
            "expected_condition": "Possible digestive issue"
        },
        {
            "name": "New Disease Expansion (Jaundice)",
            "input": "yellow eyes and yellow skin",
            "expected_condition": "Possible jaundice or liver-related condition"
        },
        {
            "name": "New Disease Expansion (Asthma)",
            "input": "feeling chest tightness and severe wheezing",
            "expected_condition": "Possible asthma or breathing distress"
        },
        {
            "name": "New Disease Expansion (HFMD)",
            "input": "vaai pun and hand rash", # Tamil + English mix
            "expected_condition": "Possible Hand, Foot, and Mouth Disease (HFMD)"
        }
    ]

    print("--- PHASE 1 VERIFICATION START ---")
    for t in tests:
        print(f"\nTest: {t['name']}")
        try:
            print(f"Input: {t['input']}")
        except UnicodeEncodeError:
            print("Input: [Tamil/Bilingual Text - Encoding hidden]")
        
        result = analyze_symptoms(t['input'])
        print(f"Detected Condition: {result['condition']}")
        print(f"Urgency: {result['urgency']}")
        print(f"Symptoms: {result['detected_symptoms']}")
        
    print("\n--- PHASE 1 VERIFICATION END ---")

if __name__ == "__main__":
    test_engine()
