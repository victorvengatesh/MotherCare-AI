import pytest
from app.services.clinical_library import SYMPTOM_LIBRARY
from app.services.interview_engine import (
    process_clinical_query,
    clear_session,
    get_session,
    save_session,
    calculate_step_risk
)

def test_symptom_matching_starts_session():
    user_id = "test_user_123"
    clear_session(user_id)
    
    twin_data = {"current_week": 12, "systolic_bp": 120, "diastolic_bp": 80}
    
    # Query with symptom that exists in library (headache)
    res = process_clinical_query(
        query="I have a terrible headache",
        user_id=user_id,
        twin_data=twin_data,
        language="English",
        action="submit"
    )
    
    assert res is not None
    assert res["completed"] is False
    assert res["step_number"] == 1
    assert "severe_headache" in get_session(user_id)["symptom_key"]
    
    # Clean up
    clear_session(user_id)


def test_questionnaire_sequential_steps():
    user_id = "test_user_456"
    clear_session(user_id)
    
    twin_data = {"current_week": 28, "systolic_bp": 120, "diastolic_bp": 80}
    
    # Step 1: Start
    res1 = process_clinical_query(
        query="I have blurry vision",
        user_id=user_id,
        twin_data=twin_data
    )
    assert res1["completed"] is False
    assert res1["step_number"] == 1
    
    # Step 2: Answer first question
    res2 = process_clinical_query(
        query="yes, seeing spots",
        user_id=user_id,
        twin_data=twin_data
    )
    assert res2["completed"] is False
    assert res2["step_number"] == 2
    
    # Clean up
    clear_session(user_id)


def test_calculate_step_risk():
    session = {
        "answers": {
            "Do you have blurred vision?": "yes, severe spots"
        }
    }
    twin_data = {"systolic_bp": 145, "diastolic_bp": 95}
    
    risk = calculate_step_risk(session, twin_data)
    assert risk == "Urgent Assessment 🟠"


def test_emergency_override_bypass():
    user_id = "test_user_emergency"
    clear_session(user_id)
    
    twin_data = {"current_week": 32}
    
    res = process_clinical_query(
        query="I am experiencing heavy bleeding and soaking a pad",
        user_id=user_id,
        twin_data=twin_data
    )
    
    assert res is not None
    assert res["completed"] is True
    assert "Emergency Care" in res["risk_level"]
    assert "CLINICAL EMERGENCY DETECTED" in res["response"]
    
    # Verify session is cleaned up
    assert get_session(user_id) is None
