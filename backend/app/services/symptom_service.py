def analyze_symptoms(symptoms: str) -> dict:
    text = symptoms.lower()
    
    # Base categories and patterns
    categories = [
        {
            "keywords": ["infection", "pus", "fever", "spreading", "warmth", "severe swelling"],
            "condition": "Possible infection or worsening skin condition",
            "urgency": "Moderate to High",
            "advice": "Keep the area clean. Monitor for increasing fever or spreading redness. Please seek medical evaluation soon."
        },
        {
            "keywords": ["burn", "blister", "scald", "heat", "fire"],
            "condition": "Possible minor burn",
            "urgency": "Moderate",
            "advice": "Cool the area with clean, running water. Avoid applying oil, toothpaste, or home remedies. Seek care if blistering is extensive."
        },
        {
            "keywords": ["cut", "bleeding", "wound", "injury", "laceration"],
            "condition": "Possible wound or skin injury",
            "urgency": "Moderate",
            "advice": "Clean the wound with mild soap and water. Apply pressure if bleeding. Seek medical care if the wound is deep or won't stop bleeding."
        },
        {
            "keywords": ["itching", "redness", "rash", "allergy", "irritation", "burning sensation", "swelling"],
            "condition": "Possible skin allergy or irritation",
            "urgency": "Low to Moderate",
            "advice": "Avoid scratching. Use mild, fragrance-free cleansers. If you suspect an allergic reaction, identify and remove the potential trigger."
        }
    ]

    # Caution / Red Flag detection
    caution_keywords = ["fever", "pus", "spreading", "severe pain", "heavy bleeding", "deep"]
    found_caution = [word for word in caution_keywords if word in text]
    
    # Find matching category
    result = None
    for cat in categories:
        if any(word in text for word in cat["keywords"]):
            result = cat.copy()
            break
            
    if not result:
        result = {
            "condition": "Unclear skin-related condition",
            "urgency": "Low to Moderate",
            "advice": "Keep a close eye on the area. If symptoms persist or worsen, please consult a healthcare professional."
        }

    # Urgency escalation logic
    if found_caution:
        if "Low" in result["urgency"] and "Moderate" not in result["urgency"]:
            result["urgency"] = "Moderate"
        elif "Low to Moderate" in result["urgency"]:
            result["urgency"] = "Moderate to High"
        elif "Moderate" in result["urgency"] and "High" not in result["urgency"]:
            result["urgency"] = "Moderate to High"
        elif "Moderate to High" in result["urgency"]:
            result["urgency"] = "High"
            
        # Add warning to advice
        caution_text = ", ".join(found_caution)
        result["advice"] += f" Caution: Detected signs like {caution_text} which may indicate a more serious condition."

    return result
