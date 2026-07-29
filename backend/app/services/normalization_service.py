import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("normalization-service")

# Load vocabulary JSON
VOCAB_PATH = Path(__file__).resolve().parent.parent / "config" / "vocabulary.json"

def load_vocabulary() -> Dict[str, str]:
    try:
        with open(VOCAB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load vocabulary config: %s", e)
        return {}

VOCABULARY = load_vocabulary()

def detect_language(text: str) -> str:
    # Check for Tamil script (range U+0B80 to U+0BFF)
    if any("\u0b80" <= char <= "\u0bff" for char in text):
        return "Tamil"
    
    # Check for Tanglish based on typical suffixes or vocab keys
    tanglish_indicators = [
        "vali", "iruku", "irukku", "mudila", "moochu", "kashtam", "asaiyala",
        "raththam", "ratham", "veekam", "kuzhandhai", "kuzhandai", "romba",
        "varuthu", "valikithu", "valikku", "illa", "illai", "mayakkam", "valippu"
    ]
    text_lower = text.lower()
    if any(ind in text_lower for ind in tanglish_indicators):
        return "Tanglish"
    
    return "English"

def normalize_tamil_text(text: str) -> str:
    """Strip common colloquial Tamil suffixes to help dictionary match."""
    suffixes = [
        r"இருக்கு$", r"இருக்குது$", r"இருக்குனு$", 
        r"வலிகுது$", r"வலிக்குது$", r"வலிக்கிது$",
        r"பண்ணுது$", r"வருது$", r"உள்ளது$"
    ]
    processed = text
    for suffix in suffixes:
        processed = re.sub(suffix, "", processed)
    return processed.strip()

def normalize_tanglish_text(text: str) -> str:
    """Normalize common Tanglish spelling variations (e.g. double letters)."""
    text = text.lower()
    text = text.replace("raththam", "ratham")
    text = text.replace("kuzhandhai", "kuzhandai")
    return text.strip()

def check_negation(text: str, match_index: int, match_key: str, detected_lang: str = None) -> bool:
    """
    Checks if a matched symptom term is negated in the nearby text context.
    Uses directional checks depending on the language:
    - English: check preceding context (before_text)
    - Tamil/Tanglish: check trailing context (after_text)
    It avoids crossing sentence or clause boundaries like period, semicolon, and conjunctions.
    """
    if detected_lang is None:
        detected_lang = detect_language(text)

    text_lower = text.lower()
    
    # Increase context window to 50 characters to catch trailing colloquial negators
    before_text = text_lower[max(0, match_index - 50):match_index]
    after_text = text_lower[match_index + len(match_key):min(len(text_lower), match_index + len(match_key) + 50)]

    english_negations = [r"\bno\b", r"\bnot\b", r"\bdon't\b", r"\bdont\b"]
    tamil_tanglish_negations = [r"இல்லை", r"இல்ல", r"\billa\b", r"\billai\b", r"இல்லைனு"]

    # Boundary indicators that stop a negation from propagating
    boundary_patterns = [r"\.", r";", r"!", r"\?", r"\bbut\b", r"\band\b", r"ஆனால்", r"\baana\b", r"\bana\b", r"மற்றும்"]

    # 1. Check preceding context (for English negations)
    for neg in english_negations:
        for m in re.finditer(neg, before_text):
            intervening = before_text[m.end():]
            if not any(re.search(bp, intervening) for bp in boundary_patterns):
                return True

    # 2. Check trailing context (for Tamil/Tanglish negations)
    if detected_lang != "English":
        for neg in tamil_tanglish_negations:
            for m in re.finditer(neg, after_text):
                intervening = after_text[:m.start()]
                if not any(re.search(bp, intervening) for bp in boundary_patterns):
                    return True

    return False

def extract_duration(text: str) -> str:
    """Extract durations in English and Tamil."""
    english_pattern = r"\b(\d+|one|two|three|four|five|six|seven)\s*(day|days|week|weeks|month|months|hour|hours)\b"
    tamil_pattern = r"(\d+|ஒரு|இரண்டு|மூன்று|நான்கு|ஐந்து)\s*(நாள்|நாட்கள்|வாரம்|வாரங்கள்|மணி|மணிநேரம்)"
    
    match_eng = re.search(english_pattern, text, re.IGNORECASE)
    if match_eng:
        return match_eng.group(0)
        
    match_tam = re.search(tamil_pattern, text)
    if match_tam:
        return match_tam.group(0)
        
    return ""

def extract_severity(text: str) -> str:
    """Extract severity cues in English, Tamil, and Tanglish."""
    severities = {
        "Severe": ["severe", "intense", "sharp", "கடுமையான", "அதிகமான", "romba", "kadu", "heavy"],
        "Moderate": ["moderate", "elevated", "மிதமான", "கொஞ்சம்", "slight", "sathiri"],
        "Mild": ["mild", "slight", "siru", "slight", "lesana", "லேசான"]
    }
    text_lower = text.lower()
    for level, words in severities.items():
        if any(w in text_lower for w in words):
            return level
    return "Standard"

def process_multilingual_input(raw_text: str) -> Dict[str, Any]:
    """
    NLP service pipeline:
    1. Language Detection
    2. Normalize text based on detected language
    3. Extract symptoms mapped to canonical English terms
    4. Detect negation, duration, severity
    5. Find unrecognized / uncertain terms requiring clinical review
    """
    lang = detect_language(raw_text)
    normalized = raw_text
    
    if lang == "Tamil":
        normalized = normalize_tamil_text(raw_text)
    elif lang == "Tanglish":
        normalized = normalize_tanglish_text(raw_text)
        
    extracted_symptoms = []
    negated_symptoms = []
    matched_ranges = []
    
    # 1. Match vocabulary keys
    text_lower = normalized.lower()
    raw_lower = raw_text.lower()
    
    for vocab_key, canonical in VOCABULARY.items():
        # Match inside the normalized text or raw text
        for text_to_check in [text_lower, raw_lower]:
            start_idx = text_to_check.find(vocab_key)
            if start_idx != -1:
                # Store the match range in raw/normalized to check for overlaps
                match_range = (start_idx, start_idx + len(vocab_key))
                
                # Check for negation
                is_negated = check_negation(raw_text, start_idx, vocab_key, lang)
                
                if is_negated:
                    if canonical not in negated_symptoms:
                        negated_symptoms.append(canonical)
                else:
                    if canonical not in extracted_symptoms:
                        extracted_symptoms.append(canonical)
                
                matched_ranges.append(match_range)
                break  # match found for this key

    # 2. Check Negated overrides (if symptom was matched as both, prefer negated if overall negated)
    for neg in negated_symptoms:
        if neg in extracted_symptoms:
            extracted_symptoms.remove(neg)

    # 3. Identify uncertain terms
    # If the user input mentions general symptoms or pain indicators but isn't matched fully
    uncertain_terms = []
    requires_clinical_review = False
    
    pain_indicators = ["வலி", "vali", "pain", "cramp", "kashtam", "கஷ்டம்", "veekam", "வீக்கம்"]
    for ind in pain_indicators:
        if ind in raw_lower:
            # Check if we mapped it to a specific canonical symptom
            # If we didn't map a specific location (like abdomen, chest, head) but there is generic mention of pain
            is_mapped = False
            for sym in extracted_symptoms + negated_symptoms:
                if any(p in sym for p in ["pain", "bleeding", "headache", "movement", "breathing", "swelling"]):
                    is_mapped = True
            if not is_mapped:
                uncertain_terms.append(f"Generic mention of '{ind}'")
                requires_clinical_review = True

    # 4. Check for completely unrecognized words (for all languages)
    # Split words, check if any word contains letters but isn't in vocabulary or common helper words
    words = re.findall(r"\b\w+\b", raw_lower)
    common_helpers = {
        "have", "with", "feeling", "romba", "iruku", "illa", "illai", "very", "pain", "feel", "strange", 
        "yesterday", "morning", "since", "about", "some", "mild", "severe", "moderate", "hours", "days", 
        "weeks", "months", "low", "high", "normal", "baby", "movement", "fetal", "doctor", "care", "need", 
        "help", "please", "fever", "vomiting", "bleeding", "headache", "breathing", "swelling", "chest", 
        "vision", "seizure", "blurry", "stomach", "abdominal", "cramp", "cramps", "backache", "nausea", 
        "fatigue", "tired", "sleepy", "itching", "itchy", "rash", "spots"
    }
    for w in words:
        # Skip short words and standard words or numbers
        if len(w) <= 3 or w.isdigit() or w in common_helpers:
            continue
        # Check if this word is a substring of any vocabulary key
        is_part_of_vocab = False
        for vk in VOCABULARY.keys():
            if w in vk or vk in w:
                is_part_of_vocab = True
                break
        if not is_part_of_vocab:
            # Save unrecognized terms
            uncertain_terms.append(w)
            requires_clinical_review = True

    # Limit uncertain terms list size and make values unique
    uncertain_terms = list(set(uncertain_terms))[:5]

    return {
        "original_text": raw_text,
        "detected_language": lang,
        "normalized_text": normalized,
        "extracted_symptoms": extracted_symptoms,
        "negated_symptoms": negated_symptoms,
        "uncertain_terms": uncertain_terms,
        "requires_clinical_review": requires_clinical_review,
        "duration": extract_duration(raw_text),
        "severity": extract_severity(raw_text)
    }
