import json
import logging
import os
from typing import Dict

from app.services.rag_service import get_relevant_context
from app.utils.ai_wrapper import call_ai_with_retry

logger = logging.getLogger("orchestrator")

SPECIALIST_PROFILES: Dict[str, str] = {
    "nutritionist": (
        "You are a certified prenatal nutritionist. "
        "You specialise in gestational diabetes prevention, iron-rich diets, "
        "folate intake, and healthy weight management during pregnancy."
    ),
    "obgyn": (
        "You are a board-certified OB-GYN. "
        "You specialise in maternal clinical health, pregnancy complications, "
        "labour signs, foetal development, and postpartum care."
    ),
    "mental_health": (
        "You are a maternal mental health counsellor. "
        "You specialise in postpartum depression, prenatal anxiety, "
        "stress management, and emotional wellbeing for new mothers."
    ),
    "emergency": (
        "You are a maternal emergency triage specialist. "
        "You identify critical red-flag symptoms such as severe headaches, "
        "vision changes, heavy bleeding, chest pain, and reduced foetal movement. "
        "You always recommend immediate emergency care when required."
    ),
}

from app.services.redflag_service import screen_symptoms

def _get_client():
    """Returns an initialised google-genai client or None."""
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _select_agent(query: str, twin_data: dict, client) -> str:
    """CMO Agent: decides which specialist handles this query."""
    query_lower = query.lower()
    # Hard-coded emergency override — safety first
    safety_result = screen_symptoms(query)
    if safety_result["requires_immediate_care"]:
        return "emergency"

    if client is None:
        # Keyword fallback when Gemini unavailable
        if any(w in query_lower for w in ["eat", "diet", "food", "nutrition", "glucose", "iron", "weight"]):
            return "nutritionist"
        if any(w in query_lower for w in ["sad", "anxious", "depress", "stress", "mood", "cry", "scared"]):
            return "mental_health"
        return "obgyn"

    # CMO Prompt — structured JSON response
    cmo_prompt = f"""You are the Chief Medical Officer Agent for MotherCare AI.
Patient twin state summary: week {twin_data.get('current_week', 'unknown')}, 
BP {twin_data.get('systolic_bp','?')}/{twin_data.get('diastolic_bp','?')}, 
glucose {twin_data.get('glucose_level','?')} mg/dL, 
hemoglobin {twin_data.get('hemoglobin','?')} g/dL.

Patient query: "{query}"

Available specialists: {list(SPECIALIST_PROFILES.keys())}

Respond ONLY with valid JSON in this exact format (no markdown):
{{"selected_agent": "<agent_name>", "reason": "<one sentence>"}}"""

    # Wrap the call
    fallback_json = '{"selected_agent": "obgyn", "reason": "fallback"}'
    text = call_ai_with_retry(
        client=client,
        model="gemini-2.5-flash",
        contents=cmo_prompt,
        agent_name="cmo",
        fallback_text=fallback_json
    )

    try:
        text = text.strip().lstrip("```json").rstrip("```").strip()
        data = json.loads(text)
        agent = data.get("selected_agent", "obgyn")
        if agent not in SPECIALIST_PROFILES:
            agent = "obgyn"
        logger.info("CMO selected: %s — %s", agent, data.get("reason", ""))
        return agent
    except Exception as e:
        logger.warning("CMO selection parsing failed (%s), defaulting to obgyn. text=%s", e, text)
        return "obgyn"


from sqlalchemy.orm import Session

def run_consultation(
    query: str,
    user_id: str,
    twin_data: dict,
    language: str = "English",
    db: Session = None,
    action: str = "submit",
    question_to_edit: str | None = None,
    new_value: str | None = None
) -> dict:
    """
    Full orchestration pipeline:
      0. Clinical Interview Engine (Pregnancy symptom diagnostic loops)
      1. RAG context retrieval
      2. CMO agent selection
      3. Specialist response generation
    """
    client = _get_client()

    # 0. Clinical Interview & Diagnostic Engine Triage
    from app.services.interview_engine import process_clinical_query
    clinical_res = process_clinical_query(
        query=query,
        user_id=user_id,
        twin_data=twin_data,
        language=language,
        client=client,
        action=action,
        question_to_edit=question_to_edit,
        new_value=new_value
    )
    if clinical_res is not None:
        return {
            "agent": clinical_res["agent"],
            "agent_label": clinical_res["agent_label"],
            "response": clinical_res["response"],
            "rag_context_used": False,
            "citations": [],
            "language": language,
            "risk_level": clinical_res.get("risk_level"),
            "completed": clinical_res.get("completed", False),
            "step_number": clinical_res.get("step_number", 0),
            "total_steps": clinical_res.get("total_steps", 0),
            "collected_symptoms": clinical_res.get("collected_symptoms", []),
            "answers": clinical_res.get("answers", {})
        }

    # 0. Safety Layer
    safety_result = screen_symptoms(query)
    if safety_result["requires_immediate_care"]:
        return {
            "agent": "emergency",
            "agent_label": "Emergency Specialist",
            "response": f"🚨 EMERGENCY ALERT: {safety_result['reason']}\n\n{safety_result['recommended_action']}\n\nThis is an automated safety screening, not a diagnosis. Please get help immediately.",
            "rag_context_used": False,
            "language": language,
            "safety_flags": safety_result["detected_red_flags"]
        }

    # 1. RAG — pull relevant context
    close_db = False
    if db is None:
        from app.db.database import SessionLocal
        db = SessionLocal()
        close_db = True

    rag_context = ""
    citations = []
    try:
        rag_context, citations = get_relevant_context(db, query, user_id)
    except Exception as e:
        logger.error(f"Error retrieving RAG context: {e}")
    finally:
        if close_db:
            db.close()

    # 2. CMO — select specialist
    selected_agent = _select_agent(query, twin_data, client)
    agent_role = SPECIALIST_PROFILES[selected_agent]

    # 3. Specialist prompt
    language_instruction = (
        "Respond in Tamil (தமிழ்)." if language == "Tamil"
        else "Respond in clear, simple English."
    )

    context_block = (
        f"\n\n--- Relevant Context ---\n{rag_context}" if rag_context and rag_context != "insufficient approved information" else ""
    )

    twin_block = (
        f"\n\n--- Patient Digital Twin ---\n"
        f"Pregnancy week: {twin_data.get('current_week', 'unknown')}\n"
        f"BP: {twin_data.get('systolic_bp','?')}/{twin_data.get('diastolic_bp','?')} mmHg\n"
        f"Glucose: {twin_data.get('glucose_level','?')} mg/dL\n"
        f"Hemoglobin: {twin_data.get('hemoglobin','?')} g/dL\n"
        f"BMI: {twin_data.get('bmi','?')}"
    ) if twin_data else ""

    specialist_prompt = f"""{agent_role}

You are responding through MotherCare AI, a healthcare assistant for mothers and families.
{language_instruction}
Be warm, empathetic, and concise (4–6 sentences). Always end with a reminder to consult a real doctor for diagnosis.{twin_block}{context_block}

Patient question: {query}"""

    response_text = call_ai_with_retry(
        client=client,
        model="gemini-2.5-flash",
        contents=specialist_prompt,
        agent_name=selected_agent
    )

    return {
        "agent": selected_agent,
        "agent_label": selected_agent.replace("_", " ").title(),
        "response": response_text,
        "rag_context_used": bool(citations),
        "citations": citations,
        "language": language,
    }
