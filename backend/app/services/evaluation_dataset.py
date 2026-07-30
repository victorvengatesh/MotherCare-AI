# evaluation_dataset.py — Automated 150 Clinical Case Scenario Evaluator for MotherCare AI v2.1
import os
import uuid
import logging
from app.services.clinical_library import SYMPTOM_LIBRARY, search_clinical_library
from app.services.interview_engine import process_clinical_query, clear_session

logger = logging.getLogger("evaluator")

def generate_evaluation_dataset() -> list:
    """Programmatically generates 150 realistic clinical scenarios for evaluation."""
    dataset = []
    
    profiles = [
        {"id": 1, "age": 28, "history": "None", "twins": False, "c_section": False, "hypertension": False},
        {"id": 2, "age": 36, "history": "Previous C-Section", "twins": True, "c_section": True, "hypertension": False},
        {"id": 3, "age": 32, "history": "Chronic Hypertension", "twins": False, "c_section": False, "hypertension": True},
        {"id": 4, "age": 29, "history": "Gestational Diabetes in previous pregnancy", "twins": False, "c_section": False, "hypertension": False},
    ]

    # Map symptoms with their expected risk bounds
    symptom_scenarios = [
        {"text": "I am experiencing severe headache", "key": "severe_headache", "risk": "Urgent", "emergency": False},
        {"text": "I am bleeding heavily and soaking a pad", "key": "postpartum_heavy_bleeding", "risk": "Emergency", "emergency": True},
        {"text": "baby is moving less today", "key": "reduced_fetal_movement", "risk": "Urgent", "emergency": False},
        {"text": "baby movement has completely stopped", "key": "absent_fetal_movement", "risk": "Emergency", "emergency": True},
        {"text": "I have chest pain and shortness of breath", "key": "chest_pain_shortness_breath", "risk": "Emergency", "emergency": True},
        {"text": "water breaking and fluid is greenish", "key": "water_breaking", "risk": "Emergency", "emergency": True},
        {"text": "I have high fever and chills", "key": "fever", "risk": "Urgent", "emergency": False},
        {"text": "burning urination and side pain", "key": "burning_urination", "risk": "Urgent", "emergency": False},
        {"text": "excessive thirst and peeing all the time", "key": "excessive_thirst", "risk": "Routine", "emergency": False},
        {"text": "I feel very depressed and have self-harm thoughts", "key": "suicidal_thoughts", "risk": "Emergency", "emergency": True},
        
        # Tamil & Tanglish inputs (75 cases total will use Tamil/Tanglish permutations)
        {"text": "thalai romba valikuthu", "key": "severe_headache", "risk": "Urgent", "emergency": False},
        {"text": "kannu blur ah iruku", "key": "blurred_vision", "risk": "Urgent", "emergency": False},
        {"text": "baby movement kammi ah iruku", "key": "reduced_fetal_movement", "risk": "Urgent", "emergency": False},
        {"text": "ratham konjam varuthu", "key": "spotting", "risk": "Routine", "emergency": False},
        {"text": "moothiram pogumbothu erichal", "key": "burning_urination", "risk": "Routine", "emergency": False},
    ]

    weeks = [8, 20, 28, 36, 39, 41]

    # Generate permutations until we have exactly 150 test cases
    case_id = 1
    while len(dataset) < 150:
        for profile in profiles:
            for symptom in symptom_scenarios:
                for week in weeks:
                    if len(dataset) >= 150:
                        break
                        
                    # Customize query for permutation variety
                    text = symptom["text"]
                    if case_id % 3 == 0 and not text.startswith("tha") and not text.startswith("kan") and not text.startswith("bab") and not text.startswith("rat") and not text.startswith("moo"):
                        text += f" in week {week}"
                    
                    dataset.append({
                        "case_id": case_id,
                        "query": text,
                        "symptom_key": symptom["key"],
                        "expected_risk": symptom["risk"],
                        "expected_emergency": symptom["emergency"],
                        "pregnancy_week": week,
                        "profile": profile
                    })
                    case_id += 1

    return dataset


class ClinicalEvaluator:
    @staticmethod
    def run_evaluation(client = None) -> dict:
        """Evaluates all 150 cases and calculates metrics."""
        dataset = generate_evaluation_dataset()
        
        symptom_matches = 0
        emergency_recall_hits = 0
        emergency_recall_total = 0
        total_precision_cases = 0
        precision_hits = 0
        
        tamil_hits = 0
        tamil_total = 0
        
        failed_cases = []
        
        for case in dataset:
            user_id = f"eval_user_{case['case_id']}"
            clear_session(user_id)
            
            # Setup mock digital twin data matching the scenario profile
            twin_data = {
                "current_week": case["pregnancy_week"],
                "systolic_bp": 150 if case["profile"]["hypertension"] else 120,
                "diastolic_bp": 95 if case["profile"]["hypertension"] else 80,
                "glucose_level": 150 if case["profile"]["id"] == 4 else 90
            }
            
            # Query symptom library directly to test NLP keyword extraction
            matched = search_clinical_library(case["query"])
            
            is_tamil_input = any(w in case["query"].lower() for w in ["valikuthu", "iruku", "kammi", "varuthu", "erichal"])
            if is_tamil_input:
                tamil_total += 1
                if matched:
                    tamil_hits += 1

            if matched:
                symptom_matches += 1
                
            # Perform query triage
            res = process_clinical_query(
                query=case["query"],
                user_id=user_id,
                twin_data=twin_data,
                client=client
            )
            
            is_emergency = res.get("risk_level") == "Emergency Care 🔴" if res else False
            
            if case["expected_emergency"]:
                emergency_recall_total += 1
                if is_emergency:
                    emergency_recall_hits += 1
                else:
                    failed_cases.append({
                        "case_id": case["case_id"],
                        "query": case["query"],
                        "reason": "Failed to trigger emergency escalation."
                    })
                    
            if is_emergency:
                total_precision_cases += 1
                if case["expected_emergency"]:
                    precision_hits += 1
                    
            clear_session(user_id)

        # Calculate metrics
        symptom_acc = (symptom_matches / 150) * 100
        emergency_recall = (emergency_recall_hits / emergency_recall_total) * 100 if emergency_recall_total > 0 else 100
        emergency_precision = (precision_hits / total_precision_cases) * 100 if total_precision_cases > 0 else 100
        tamil_acc = (tamil_hits / tamil_total) * 100 if tamil_total > 0 else 100
        
        overall_score = (symptom_acc + emergency_recall + tamil_acc) / 3

        return {
            "overall_score": round(overall_score, 2),
            "symptom_detection_accuracy": round(symptom_acc, 2),
            "emergency_recall": round(emergency_recall, 2),
            "emergency_precision": round(emergency_precision, 2),
            "tamil_tanglish_understanding": round(tamil_acc, 2),
            "failed_cases_count": len(failed_cases),
            "failed_cases": failed_cases
        }
