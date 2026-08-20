from app.services.redflag_service import screen_symptoms


def test_screen_symptoms_english_emergency():
    res = screen_symptoms("I have severe pain in my stomach")
    assert res["requires_immediate_care"] is True
    assert "Severe abdominal/pelvic pain" in res["detected_red_flags"]


def test_screen_symptoms_tamil_emergency():
    res = screen_symptoms("எனக்கு கடுமையான வலி உள்ளது")
    assert res["requires_immediate_care"] is True
    assert "Severe pain / Breathlessness (Tamil)" in res["detected_red_flags"]


def test_screen_symptoms_tanglish_emergency():
    res = screen_symptoms("romba vali ah iruku")
    assert res["requires_immediate_care"] is True
    assert "Severe pain / Breathlessness (Tanglish)" in res["detected_red_flags"]


def test_screen_symptoms_normal():
    res = screen_symptoms("I have a slight headache")
    assert res["requires_immediate_care"] is False


def test_negated_emergency_phrase_is_conservatively_flagged():
    """Document the current safety-first behavior until negation is validated.

    The rule engine intentionally prefers a false positive over silently
    downgrading an emergency phrase. A future clinically validated negation
    model can change this expectation together with its evaluation dataset.
    """
    res = screen_symptoms("I do not have severe pain")
    assert res["requires_immediate_care"] is True
    assert "Severe abdominal/pelvic pain" in res["detected_red_flags"]
