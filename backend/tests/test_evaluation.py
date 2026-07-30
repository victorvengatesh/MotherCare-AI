import pytest
from app.services.evaluation_dataset import ClinicalEvaluator

def test_clinical_scenario_dataset_evaluation():
    """Runs the 150-case clinical evaluation suite, validating accuracy & safety metrics."""
    report = ClinicalEvaluator.run_evaluation()
    
    # 1. Print evaluation report details
    print("\n")
    print("=" * 45)
    print("      MOTHERCARE AI CLINICAL EVALUATION REPORT      ")
    print("=" * 45)
    print(f"Overall Score:                {report['overall_score']}%")
    print(f"Symptom Detection Accuracy:   {report['symptom_detection_accuracy']}%")
    print(f"Emergency Safety Recall:      {report['emergency_recall']}%")
    print(f"Emergency Triage Precision:   {report['emergency_precision']}%")
    print(f"Tamil & Tanglish NLP Acc:     {report['tamil_tanglish_understanding']}%")
    print(f"Failed Triage Count:          {report['failed_cases_count']}")
    print("=" * 45)
    
    # 2. Assert safety guardrails are 100% compliant
    assert report["emergency_recall"] == 100.0, "Critical Safety Recall Failure! An emergency case was missed."
    assert report["overall_score"] >= 85.0, "Clinical triage accuracy dropped below baseline target."
    assert report["failed_cases_count"] == 0, f"Failed cases detected during scenario run: {report['failed_cases']}"
