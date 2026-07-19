import os
import logging
from google import genai

logger = logging.getLogger("gemini-service")

# Lazy-initialize client so missing key doesn't crash import
_client = None

def _get_client() -> genai.Client | None:
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — Gemini enhancement disabled.")
        return None
    _client = genai.Client(api_key=api_key)
    return _client


def enhance_response(
    symptoms: str,
    symptom_result: dict,
    image_result: dict | None = None,
) -> str | None:
    """
    Sends the structured triage result to Gemini 2.5 Flash and returns a
    friendly, plain-language explanation for the patient.

    Returns None if the API key is missing or the call fails, so the
    caller can fall back to the rule-based response gracefully.
    """
    client = _get_client()
    if client is None:
        return None

    # Build a concise context block for the model
    condition   = symptom_result.get("condition", "Unclear")
    urgency     = symptom_result.get("urgency", "Moderate")
    advice      = symptom_result.get("advice", "")
    has_duration = symptom_result.get("has_duration", False)

    image_context = ""
    if image_result and image_result.get("ml_result"):
        ml = image_result["ml_result"]
        if ml.get("status") == "success":
            image_context = (
                f"\nImage analysis detected: {ml.get('predicted_class', 'unknown')} "
                f"(confidence: {ml.get('confidence', 0):.0%}, "
                f"interpretation: {ml.get('interpretation', 'unclear')})."
            )

    prompt = f"""You are a compassionate medical triage assistant for MotherCare AI, \
a healthcare app that supports mothers and families.

A patient has reported the following symptoms: "{symptoms}"

Our triage engine has already assessed:
- Condition group: {condition}
- Urgency level: {urgency}
- Persistent/duration detected: {has_duration}{image_context}
- Initial advice: {advice}

Based on this assessment, write a warm, clear, and concise response (3–5 sentences) for the patient that:
1. Acknowledges their symptoms with empathy.
2. Explains what the condition might be in simple language (avoid medical jargon).
3. Clearly states the urgency and what action they should take.
4. Ends with a reminder that this is preliminary guidance and they should consult a doctor.

Do NOT mention confidence scores, model names, or internal system details.
Write only the patient-facing message — no headers, no bullet points, just flowing text."""

    try:
        from app.utils.ai_wrapper import call_ai_with_retry
        text = call_ai_with_retry(
            client=client,
            model="gemini-2.5-flash",
            contents=prompt,
            agent_name="enhancement",
            fallback_text=""
        )
        if text:
            logger.info("Gemini enhancement generated (%d chars).", len(text))
            return text
        return None
    except Exception as e:
        logger.error("Gemini API call failed unexpectedly: %s", e)
        return None
