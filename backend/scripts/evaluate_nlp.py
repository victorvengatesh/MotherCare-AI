import os
import sys
from pathlib import Path


# Add backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.normalization_service import process_multilingual_input

# Evaluation dataset (synthetic, no real patient data)
EVAL_DATASET = [
    {
        "id": 1,
        "input": "I have vaginal bleeding since yesterday morning",
        "expected_lang": "English",
        "expected_symptom": "bleeding",
        "is_negated": False,
        "is_emergency": True
    },
    {
        "id": 2,
        "input": "காய்ச்சல் மற்றும் கடுமையான தலை வலி",
        "expected_lang": "Tamil",
        "expected_symptom": "fever",  # or headache (காய்ச்சல் / தலை வலி)
        "is_negated": False,
        "is_emergency": False  # fever and headache are moderate/high, but bleeding/fetal movement are emergency red flags
    },
    {
        "id": 3,
        "input": "vomiting romba iruku enaku kai kaal veekam iruku",
        "expected_lang": "Tanglish",
        "expected_symptom": "severe vomiting",  # vomiting romba iruku / kai kaal veekam
        "is_negated": False,
        "is_emergency": False
    },
    {
        "id": 4,
        "input": "kuzhandhai asaiyave illa today",
        "expected_lang": "Tanglish",
        "expected_symptom": "reduced fetal movement",
        "is_negated": False,
        "is_emergency": True
    },
    {
        "id": 5,
        "input": "இரத்தப்போக்கு இல்லை",
        "expected_lang": "Tamil",
        "expected_symptom": "bleeding",
        "is_negated": True,
        "is_emergency": False
    },
    {
        "id": 6,
        "input": "I do not have difficulty breathing",
        "expected_lang": "English",
        "expected_symptom": "difficulty breathing",
        "is_negated": True,
        "is_emergency": False
    },
    {
        "id": 7,
        "input": "I have mild headache but no fever",
        "expected_lang": "English",
        "expected_symptom": "headache",
        "is_negated": False,
        "is_emergency": False
    },
    {
        "id": 8,
        "input": "mayakkam and thalai vali. kai kaal veekam illai.",
        "expected_lang": "Tanglish",
        "expected_symptom": "dizziness/fainting",
        "is_negated": False,
        "is_emergency": False
    },
    {
        "id": 9,
        "input": "vaginal ratham varuthu enaku romba thalai vali",
        "expected_lang": "Tanglish",
        "expected_symptom": "bleeding",
        "is_negated": False,
        "is_emergency": True
    },
    {
        "id": 10,
        "input": "baby movement kammiya iruku",
        "expected_lang": "Tanglish",
        "expected_symptom": "reduced fetal movement",
        "is_negated": False,
        "is_emergency": True
    },
    {
        "id": 11,
        "input": "unidentified_weird_word_here that makes it ambiguous",
        "expected_lang": "English",
        "expected_symptom": None,
        "is_negated": False,
        "is_emergency": False
    }
]

def run_evaluation():
    print("==================================================")
    print("  MOTHERCARE-AI: MULTILINGUAL NLP EVALUATION SUITE")
    print("==================================================")
    
    total = len(EVAL_DATASET)
    lang_correct = 0
    symptom_correct = 0
    negation_correct = 0
    emergency_recall_hits = 0
    emergency_expected = 0
    unknown_handled = 0
    
    results_rows = []
    
    for case in EVAL_DATASET:
        inp = case["input"]
        res = process_multilingual_input(inp)
        
        # 1. Check language detection
        lang_ok = res["detected_language"] == case["expected_lang"]
        if lang_ok:
            lang_correct += 1
            
        # 2. Check symptom normalization
        extracted = res["extracted_symptoms"]
        negated = res["negated_symptoms"]
        
        expected_sym = case["expected_symptom"]
        symptom_ok = False
        if expected_sym is None:
            symptom_ok = len(extracted) == 0
        else:
            symptom_ok = (expected_sym in extracted) or (expected_sym in negated)
            
        if symptom_ok:
            symptom_correct += 1
            
        # 3. Check negation mapping
        negation_ok = True
        if expected_sym:
            expected_neg = case["is_negated"]
            actual_neg = expected_sym in negated
            negation_ok = expected_neg == actual_neg
            print(f"CASE {case['id']} - Expected Sym: {expected_sym}, Expected Neg: {expected_neg}, Actual Neg: {actual_neg}, OK: {negation_ok}")
            if negation_ok:
                negation_correct += 1
        else:
            negation_correct += 1
            
        # 4. Check emergency mapping
        is_emergency_flagged = any(
            s in extracted for s in ["bleeding", "reduced fetal movement", "difficulty breathing", "chest pain", "seizure", "blurry vision", "severe pain"]
        )
        if case["is_emergency"]:
            emergency_expected += 1
            if is_emergency_flagged:
                emergency_recall_hits += 1
                
        # 5. Check unknown handling
        if "unidentified" in inp:
            # Should not crash and should report it or flag review
            unknown_handled += 1
            
        results_rows.append({
            "id": case["id"],
            "input": inp[:30] + "..." if len(inp) > 30 else inp,
            "expected_lang": case["expected_lang"],
            "detected_lang": res["detected_language"],
            "lang_ok": "Y" if lang_ok else "N",
            "extracted": str(extracted),
            "negated": str(negated),
            "symptom_ok": "Y" if symptom_ok else "N"
        })
        
    lang_acc = (lang_correct / total) * 100
    sym_acc = (symptom_correct / total) * 100
    neg_acc = (negation_correct / total) * 100
    em_recall = (emergency_recall_hits / emergency_expected) * 100 if emergency_expected > 0 else 100
    
    print("\n--- Summary Performance Metrics ---")
    print(f"Language Detection Accuracy:  {lang_acc:.1f}% ({lang_correct}/{total})")
    print(f"Symptom Extraction Accuracy: {sym_acc:.1f}% ({symptom_correct}/{total})")
    print(f"Negation Mapping Accuracy:    {neg_acc:.1f}% ({negation_correct}/{total})")
    print(f"Emergency Red Flag Recall:   {em_recall:.1f}% ({emergency_recall_hits}/{emergency_expected})")
    
    print("\n--- Detailed Results ---")
    print(f"{'ID':<3} | {'Input Text':<30} | {'Expected':<10} | {'Detected':<10} | {'Lang':<4} | {'Symp OK':<7} | {'Extracted':<30}")
    print("-" * 110)
    for r in results_rows:
        print(f"{r['id']:<3} | {r['input']:<30} | {r['expected_lang']:<10} | {r['detected_lang']:<10} | {r['lang_ok']:<4} | {r['symptom_ok']:<7} | {r['extracted']:<30}")
    print("==================================================")

if __name__ == "__main__":
    # Fix Windows terminal encoding for Tamil characters when run directly
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run_evaluation()
