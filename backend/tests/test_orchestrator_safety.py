import pytest
from app.agents.orchestrator import run_consultation

def test_run_consultation_emergency_override():
    # Pass twin data
    twin_data = {"current_week": 20}
    # Call orchestrator with emergency keyword
    res = run_consultation("I am bleeding heavily", "user_123", twin_data, "English")
    
    assert res["agent"] == "emergency"
    assert "🚨 EMERGENCY ALERT" in res["response"]
    assert "Vaginal bleeding" in res["safety_flags"]
