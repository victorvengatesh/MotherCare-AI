import json
import re
from pathlib import Path
import logging
from rapidfuzz import fuzz, process

logger = logging.getLogger("symptom-service")

# Path configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
KNOWLEDGE_DIR = BASE_DIR / "data" / "medical_knowledge"

def load_json(filename):
    path = KNOWLEDGE_DIR / filename
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load knowledge file {filename}: {e}")
        return {}

def normalize_text(text: str, rules: dict) -> str:
    """
    Replaces common typos with standard terms using word-boundary matching.
    """
    normalized = text
    for typo, correct in rules.items():
        # Use regex to replace only whole words
        pattern = r'\b' + re.escape(typo) + r'\b'
        normalized = re.sub(pattern, correct, normalized)
    return normalized

def extract_duration(text: str, duration_patterns: dict) -> bool:
    """
    Checks if any duration patterns (English or Tamil) are present in the text.
    """
    for lang, patterns in duration_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
    return False

def fuzzy_match_symptoms(text: str, keywords: dict, threshold: int = 80) -> set:
    """
    Uses RapidFuzz to find keyword matches in the text with a given similarity threshold.
    """
    detected = set()
    # Check for exact substring first (fast path)
    for kw, sym_id in keywords.items():
        if kw in text:
            detected.add(sym_id)
            continue
            
    # If no exact match or for typo handling, check words individually
    words = text.split()
    stop_words = {"and", "the", "have", "with", "from", "for", "this", "that"}
    for word in words:
        # Require word length > 3 and not a stop word to prevent false matches like 'and' -> 'hand'
        if len(word) <= 3 or word in stop_words:
            continue
            
        # Find best match for this word in keyword keys
        match = process.extractOne(word, keywords.keys(), scorer=fuzz.WRatio)
        if match and match[1] >= threshold:
            detected.add(keywords[match[0]])
            
    return detected

def handle_tamil_colloquial(text: str) -> str:
    """
    Preprocesses Tamil text to handle common colloquial suffixes and variations.
    """
    # Remove common suffixes that might hinder keyword matching
    suffixes = [
        r"இருக்கு$", r"இருக்குது$", r"இருக்குனு$", 
        r"வலிகுது$", r"வலிக்குது$", r"வலிக்கிது$",
        r"பண்ணுது$", r"வருது$"
    ]
    processed = text
    for suffix in suffixes:
        processed = re.sub(suffix, "", processed)
    
    # Common phonetic variations
    processed = processed.replace("வயித்து", "வயிற்று")
    processed = processed.replace("நேத்து", "நேற்று")
    
    return processed

def analyze_symptoms(symptoms: str) -> dict:
    """
    Analyzes input symptoms using a structured bilingual knowledge base with typo normalization and duration recognition.
    """
    raw_text = symptoms.lower()
    
    # Load knowledge base
    disease_groups = load_json("disease_groups.json")
    symptom_groups = load_json("symptom_groups.json")
    red_flags = load_json("red_flags.json")
    advice_templates = load_json("advice_templates.json")
    english_keywords = load_json("english_keywords.json")
    tamil_keywords = load_json("tamil_keywords.json")
    normalization_rules = load_json("normalization_rules.json")
    duration_patterns = load_json("duration_patterns.json")

    # 1. Preprocessing (Normalization & Duration)
    text = normalize_text(raw_text, normalization_rules)
    
    # Handle Tamil Colloquial variations
    tamil_processed_text = handle_tamil_colloquial(text)
    
    has_duration = extract_duration(text, duration_patterns)
    
    detected_symptom_ids = set()
    
    # 2. Keyword matching (Bilingual with Fuzzy Support)
    # Check English keywords
    eng_matches = fuzzy_match_symptoms(text, english_keywords, threshold=85)
    detected_symptom_ids.update(eng_matches)
            
    # Check Tamil keywords (using processed Tamil text)
    tam_matches = fuzzy_match_symptoms(tamil_processed_text, tamil_keywords, threshold=80)
    detected_symptom_ids.update(tam_matches)

    # 3. Identify Groups
    detected_groups = {}
    for sym_id in detected_symptom_ids:
        group_id = symptom_groups.get(sym_id)
        if group_id:
            if group_id not in detected_groups:
                detected_groups[group_id] = []
            detected_groups[group_id].append(sym_id)

    # 4. Handle Red Flags and Urgency
    is_emergency = False
    is_escalated = False
    
    emergency_list = red_flags.get("emergency_symptoms", [])
    escalation_list = red_flags.get("escalation_symptoms", [])
    
    for sym_id in detected_symptom_ids:
        if sym_id in emergency_list:
            is_emergency = True
        if sym_id in escalation_list:
            is_escalated = True

    # 5. Determine Primary Group
    primary_group_id = "unclear_condition"
    if is_emergency:
        primary_group_id = "urgent_red_flags"
    elif "fever" in detected_symptom_ids and has_duration:
        # Intelligent classification for persistent fever
        primary_group_id = "fever_general_illness"
        # Always escalate if fever has duration
        is_escalated = True
    elif detected_groups:
        # Simple heuristic: group with most matches
        primary_group_id = max(detected_groups, key=lambda k: len(detected_groups[k]))

    # 6. Build Result
    group_info = disease_groups.get(primary_group_id, disease_groups.get("unclear_condition", {"label": "Unclear", "urgency": "Low"}))
    urgency = group_info["urgency"]
    
    # Escalation logic
    if is_escalated and urgency != "High":
        if "Low" in urgency:
            urgency = "Moderate"
        elif "Moderate" in urgency and "High" not in urgency:
            urgency = "Moderate to High"

    # Advice Selection
    advice_set = advice_templates.get(primary_group_id, advice_templates.get("unclear_condition", {"default": "Consult a professional."}))
    advice = advice_set.get(urgency) or list(advice_set.values())[0]

    # Add duration context if applicable to advice
    if has_duration and primary_group_id != "urgent_red_flags":
        advice = f"Persistent symptoms detected ({symptoms}). " + advice

    return {
        "condition": group_info["label"],
        "urgency": urgency,
        "advice": advice,
        "internal_group": primary_group_id,
        "detected_symptoms": list(detected_symptom_ids),
        "has_duration": has_duration
    }


