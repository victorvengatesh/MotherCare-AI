import re
from typing import Dict, Any

# Clinical rules requiring clinician validation (Marked as requested)
# Source: General WHO/ACOG red flags for maternal health
# Note: These regex patterns MUST be clinically validated before production use.

EMERGENCY_PATTERNS = {
    # English
    r"\b(bleed|bleeding|blood)\b": "Vaginal bleeding",
    r"\b(severe|sharp|intense)\s+(pain|cramp)\b": "Severe abdominal/pelvic pain",
    r"\b(no|decreased|stopped|less)\s+(movement|kick)\b": "Decreased fetal movement",
    r"\b(chest\s+pain|breathless|can't\s+breathe|short\s+of\s+breath)\b": "Cardiopulmonary distress",
    r"\b(seizure|convulsion|fit|passed\s+out|unconscious|faint)\b": "Neurological symptoms (Seizure/Fainting)",
    r"\b(vision\s+loss|blurry|seeing\s+spots)\b": "Visual disturbances (Pre-eclampsia sign)",
    
    # Tamil (Unicode)
    r"(ரத்தம்|இரத்தம்|ரத்தப்போக்கு|ரத்தம் படுது)": "Vaginal bleeding (Tamil)",
    r"(கடுமையான வலி|நெஞ்சு வலி|மூச்சு விட முடியல|மூச்சு திணறல்)": "Severe pain / Breathlessness (Tamil)",
    r"(குழந்தை அசையல|அசைவு இல்லை|உதைக்கல)": "Decreased fetal movement (Tamil)",
    r"(மயக்கம்|வலிப்பு|கண் தெரியல|பார்வை மங்கல்)": "Seizure / Fainting / Vision issue (Tamil)",
    
    # Tanglish (Common transliteration)
    r"\b(ratham|raththam|blood varuthu|bleeding aaguthu)\b": "Vaginal bleeding (Tanglish)",
    r"\b(severe valikithu|romba vali|nenju vali|moochu vida mudila)\b": "Severe pain / Breathlessness (Tanglish)",
    r"\b(kuzhandhai asaiyala|asaiyave illa|movement illa)\b": "Decreased fetal movement (Tanglish)",
    r"\b(mayakkam|valippu|kann therila|blurry ah iruku)\b": "Seizure / Fainting / Vision issue (Tanglish)"
}

def screen_symptoms(symptoms_text: str) -> Dict[str, Any]:
    text = symptoms_text.lower()
    detected_flags = []
    
    for pattern, description in EMERGENCY_PATTERNS.items():
        if re.search(pattern, text):
            detected_flags.append(description)
            
    if detected_flags:
        return {
            "risk_level": "Emergency",
            "detected_red_flags": detected_flags,
            "reason": f"Detected critical clinical symptoms: {', '.join(detected_flags)}.",
            "recommended_action": "Seek immediate medical attention at the nearest emergency room or contact your healthcare provider urgently. Do not wait.",
            "requires_immediate_care": True
        }
        
    return {
        "risk_level": "Standard",
        "detected_red_flags": [],
        "reason": "No immediate clinical red flags detected in the query.",
        "recommended_action": "Proceed with standard screening and consultation.",
        "requires_immediate_care": False
    }
