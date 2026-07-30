# interview_engine.py — Advanced Stateful Clinical Interview & Hybrid Risk Engine for MotherCare AI v2.1
import os
import re
import json
import logging
from datetime import datetime
from app.core.caching import CacheFactory
from app.services.clinical_library import SYMPTOM_LIBRARY, CLINICAL_EMERGENCY_RULES, search_clinical_library
from app.utils.ai_wrapper import call_ai_with_retry

logger = logging.getLogger("interview-engine")

# Dedicated session cache for clinical interview sessions (expires in 15 minutes)
session_cache = CacheFactory.get_cache("clinical_sessions")
SESSION_TTL = 900

def get_session(user_id: str) -> dict | None:
    return session_cache.get(f"session:{user_id}")

def save_session(user_id: str, session_data: dict):
    session_cache.set(f"session:{user_id}", session_data, ttl=SESSION_TTL)

def clear_session(user_id: str):
    session_cache.delete(f"session:{user_id}")


def calculate_step_risk(session: dict, twin_data: dict) -> str:
    """Hybrid risk classification based on current answers, trimester, and vitals."""
    has_severe = False
    has_moderate = False
    
    # 1. Evaluate answers
    for q, a in session.get("answers", {}).items():
        a_lower = str(a).lower()
        if any(w in a_lower for w in ["heavy", "severe", "yes", "constant", "unyielding", "unrelieved", "cannot breathe", "stopped"]):
            has_severe = True
        elif any(w in a_lower for w in ["moderate", "medium", "sometimes", "light", "spotting"]):
            has_moderate = True
            
    # 2. Evaluate vitals
    systolic = twin_data.get("systolic_bp") or 120
    diastolic = twin_data.get("diastolic_bp") or 80
    glucose = twin_data.get("glucose_level") or 90
    temp = twin_data.get("body_temp") or 98.6
    
    if systolic >= 160 or diastolic >= 110:
        has_severe = True  # Severe hypertension crisis
    elif systolic >= 140 or diastolic >= 90:
        has_severe = True
    elif systolic >= 130 or diastolic >= 85:
        has_moderate = True
        
    if glucose >= 140 or glucose <= 50:
        has_severe = True  # Gestational diabetes warning or hypoglycemia drop
    elif glucose >= 110:
        has_moderate = True
        
    if temp >= 101.0:
        has_severe = True  # High fever/Infection concern

    # 3. Apply symptom combination rules (Multi-symptom modifiers)
    symptoms = session.get("all_matched_keys", [session.get("symptom_key", "")])
    if "severe_headache" in symptoms and ("blurred_vision" in symptoms or "swelling_in_face" in symptoms):
        has_severe = True  # Triad of severe pre-eclampsia
    if "vaginal_bleeding" in symptoms and "abdominal_pain" in symptoms:
        has_severe = True  # Placental abruption / threatened abortion indicator

    if has_severe:
        return "Urgent Assessment 🟠"
    if has_moderate:
        return "Routine Medical Review 🟡"
    return "Home Care 🟢"


def detect_contradiction(answers: dict, query: str) -> str | None:
    """Flags direct logical contradictions in patient answers (negation check)."""
    query_lower = query.lower()
    
    # 1. "pain" vs "no pain" contradiction
    has_no_pain = any(w in query_lower for w in ["no pain", "pain stopped", "no cramps", "vali illa", "வலி இல்லை"])
    has_pain = any(w in query_lower for w in ["severe pain", "hurts a lot", "pain is bad", "வலி இருக்கு", "valikuthu"])
    
    if has_no_pain and has_pain:
        return "You mentioned having pain and no pain in the same response. Could you please clarify if you are currently in pain?"
        
    # 2. Check historical answers contradiction
    for q, ans in answers.items():
        ans_lower = str(ans).lower()
        if "bleeding" in q.lower():
            if "spotting" in ans_lower and "soaking a pad" in query_lower:
                return "Earlier you indicated spotting, but now you mention soaking a pad. Could you clarify if the bleeding has increased?"
                
    return None


def process_clinical_query(
    query: str,
    user_id: str,
    twin_data: dict,
    language: str = "English",
    client = None,
    action: str = "submit",
    question_to_edit: str | None = None,
    new_value: str | None = None
) -> dict | None:
    """
    Stateful clinical interview engine with multi-symptom prioritization,
    contradiction flagging, step counters, and hybrid risk classification.
    """
    query_lower = query.lower()

    # 1. Emergency safety overrides (30 override rules)
    emergency_match = search_clinical_library(query)
    if emergency_match and emergency_match.get("urgency") == "Emergency":
        clear_session(user_id) # Cancel session
        return {
            "agent": "emergency",
            "agent_label": "Emergency Specialist",
            "response": f"🚨 CLINICAL EMERGENCY DETECTED: {emergency_match['matched_symptom']}\n\n{emergency_match['advice']}\n\nThis is an automated clinical safety alert. Please go to the nearest maternity triage or call emergency services immediately.",
            "completed": True,
            "risk_level": "Emergency Care 🔴",
            "safety_override": True,
            "step_number": 1,
            "total_steps": 1,
            "collected_symptoms": [emergency_match['matched_symptom']],
            "answers": {}
        }

    # 2. Get active session
    session = get_session(user_id)

    # Handle explicit reset action
    if action == "reset":
        clear_session(user_id)
        return None

    # Handle edit action
    if action == "edit" and question_to_edit and new_value:
        if session:
            session["answers"][question_to_edit] = new_value
            try:
                # Rewind asked stack to the edited question
                idx = session["required_questions"].index(question_to_edit)
                session["asked_questions"] = session["required_questions"][:idx + 1]
            except ValueError:
                pass
            save_session(user_id, session)

    if not session:
        # Start a new session. Look up symptoms.
        matched = search_clinical_library(query)
        if not matched or matched.get("emergency_triggered"):
            return None
            
        symptom_key = matched["symptom_key"]
        symptom_info = SYMPTOM_LIBRARY[symptom_key]
        
        # Multi-symptom extraction checks (prioritize dangerous combinations)
        all_matched_keys = [symptom_key]
        all_required_questions = symptom_info["required_questions"].copy()
        
        for k, info in SYMPTOM_LIBRARY.items():
            if k != symptom_key:
                for syn in info["synonyms"] + info.get("Tamil", []) + info.get("Tanglish", []):
                    if syn in query_lower and k not in all_matched_keys:
                        all_matched_keys.append(k)
                        # Merge questions without duplicates
                        for q in info["required_questions"]:
                            if q not in all_required_questions:
                                all_required_questions.append(q)
                                
        # Branching Questions logic (e.g. if headache, inject pre-eclampsia screening)
        if "severe_headache" in all_matched_keys:
            bp_q = "What is your current blood pressure reading?"
            visual_q = "Are you experiencing blurred vision or flashing lights?"
            swelling_q = "Do you have sudden swelling in your face or hands?"
            for q in [bp_q, visual_q, swelling_q]:
                if q not in all_required_questions:
                    all_required_questions.insert(0, q) # Ask critical BP questions first!

        # If pregnancy week is missing or 0.0, ask it first
        week = twin_data.get("current_week")
        if not week or week == 0.0:
            q_week = "How many weeks pregnant are you?"
            if q_week not in all_required_questions:
                all_required_questions.insert(0, q_week)
        
        session = {
            "symptom_key": symptom_key,
            "all_matched_keys": all_matched_keys,
            "original_query": query,
            "pregnancy_week": twin_data.get("current_week", "unknown"),
            "answers": {},
            "asked_questions": [],
            "required_questions": all_required_questions,
            "completed": False
        }
        logger.info(f"Started stateful clinical interview for {user_id} on: {all_matched_keys}")

    # Contradiction checks on submit
    if action == "submit" and session["asked_questions"]:
        contradiction_warning = detect_contradiction(session["answers"], query)
        if contradiction_warning:
            last_q = session["asked_questions"][-1]
            return {
                "agent": "obgyn",
                "agent_label": "Clinical Interviewer",
                "response": f"⚠️ **Contradiction Detected**: {contradiction_warning}\n\n💬 **{last_q}**",
                "completed": False,
                "risk_level": calculate_step_risk(session, twin_data),
                "step_number": len(session["asked_questions"]),
                "total_steps": len(session["required_questions"]),
                "collected_symptoms": [SYMPTOM_LIBRARY[k]["label"] for k in session["all_matched_keys"]],
                "answers": session["answers"]
            }
            
        last_q = session["asked_questions"][-1]
        session["answers"][last_q] = query
        logger.info(f"Logged answer: '{last_q}' -> '{query}'")

    # Check remaining questions
    remaining_q = [q for q in session["required_questions"] if q not in session["asked_questions"]]
    
    total_steps = len(session["required_questions"])
    step_number = len(session["asked_questions"]) + (1 if remaining_q else 0)
    step_risk = calculate_step_risk(session, twin_data)
    
    collected_symptoms = [SYMPTOM_LIBRARY[k]["label"] for k in session["all_matched_keys"]]

    if remaining_q:
        next_q = remaining_q[0]
        session["asked_questions"].append(next_q)
        save_session(user_id, session)
        
        response_text = next_q
        if language == "Tamil":
            from app.services.gemini_service import translate_response
            response_text = translate_response(next_q, "Tamil")

        return {
            "agent": "obgyn",
            "agent_label": "Clinical Interviewer",
            "response": f"To better understand your symptoms, could you please answer this follow-up question:\n\n💬 **{response_text}**",
            "completed": False,
            "risk_level": step_risk,
            "step_number": step_number,
            "total_steps": total_steps,
            "collected_symptoms": collected_symptoms,
            "answers": session["answers"]
        }

    # All questions answered! Perform final clinical reasoning
    session["completed"] = True
    clear_session(user_id)
    
    reasoning = _generate_clinical_reasoning(session, twin_data, language, client)
    
    return {
        "agent": "obgyn",
        "agent_label": "Obstetric Clinician",
        "response": reasoning["response_text"],
        "completed": True,
        "risk_level": reasoning["risk_level"],
        "clinical_handover": reasoning["clinical_handover"],
        "step_number": total_steps,
        "total_steps": total_steps,
        "collected_symptoms": collected_symptoms,
        "answers": session["answers"]
    }


def _generate_clinical_reasoning(session: dict, twin_data: dict, language: str, client) -> dict:
    """Invokes Gemini to build differential reasoning, risk stratification, and customized care plan."""
    symptom_key = session["symptom_key"]
    symptom_info = SYMPTOM_LIBRARY[symptom_key]
    
    answers_str = ""
    for q, a in session["answers"].items():
        answers_str += f"- Question: {q}\n  Answer: {a}\n"
        
    twin_str = json.dumps(twin_data, indent=2)
    
    # Check for doctor reviews/override flags to pass down
    prompt = f"""You are a board-certified consulting obstetrician assisting a pregnant mother through MotherCare AI.
Analyze the following clinical symptom case:

Primary Symptom: {symptom_info['label']}
Pregnancy Week: {session['pregnancy_week']}
Patient's Original Complaint: "{session['original_query']}"

--- Follow-up Q&A Collected ---
{answers_str}

--- Patient Digital Twin Biomarkers ---
{twin_str}

--- Reference Trimester Relevance ---
{symptom_info['trimester_relevance']}

--- Instructions ---
You must generate a structured clinical response. Keep your tone compassionate, clear, and professional.
Address the following sections exactly:
1. **Patient Summary**: Empathetic summary of what was reported.
2. **Symptoms Identified**: List of matched symptoms.
3. **Relevant History**: Analyze pregnancy week and digital twin vitals.
4. **Current Risk Level**: Classify into exactly one of: [🟢 Home Care | 🟡 Routine Medical Review | 🟠 Urgent Medical Assessment | 🔴 Emergency Care]
5. **Why This Risk Level Was Chosen**: Clear clinical explanation.
6. **Immediate Actions**: What they must do now.
7. **Things To Avoid**: List of activities/meds to avoid (e.g. do not take ibuprofen in 3rd trimester, do not stop chronic prescriptions).
8. **Home-Care Guidance**: If risk level is Home Care, provide safe guidance. Otherwise state "Follow doctor advice".
9. **Warning Signs**: Red flags to monitor.
10. **When To Seek Urgent Care**: Emergency conditions to watch.
11. **Follow-Up Plan**: Next steps.
12. **Doctor Handover Summary**: A concise clinical note for their physician in English.
13. **Evidence Sources**: Reference guideline matching (WHO maternal care guidelines).
14. **Confidence and Remaining Uncertainty**: State your evaluation confidence level (High/Moderate/Low).

Include a warning that this is clinical decision support, not an autonomous diagnosis.
For Tamil preference, translate the patient advice sections (1-11) but keep the doctor handover summary (12) in English.
"""

    try:
        from app.utils.ai_wrapper import call_ai_with_retry
        if client is None:
            from app.agents.orchestrator import _get_client
            client = _get_client()
            
        response_text = call_ai_with_retry(
            client=client,
            model="gemini-2.5-flash",
            contents=prompt,
            agent_name="obgyn_clinician",
            fallback_text="Analysis complete. Please consult your healthcare provider for evaluation."
        )
        
        if language == "Tamil":
            parts = response_text.split("#### 🩺 Doctor Handover Summary")
            from app.services.gemini_service import translate_response
            translated_advice = translate_response(parts[0], "Tamil")
            if len(parts) > 1:
                response_text = translated_advice + "\n\n#### 🩺 Doctor Handover Summary" + parts[1]
            else:
                response_text = translated_advice

        # Extract risk level
        risk_level = "Routine Medical Review 🟡"
        if "Emergency Care" in response_text or "🔴" in response_text:
            risk_level = "Emergency Care 🔴"
        elif "Urgent Medical Assessment" in response_text or "🟠" in response_text:
            risk_level = "Urgent Medical Assessment 🟠"
        elif "Home Care" in response_text or "🟢" in response_text:
            risk_level = "Home Care 🟢"

        total_steps = len(session["required_questions"])
        symptom_label = SYMPTOM_LIBRARY[session["symptom_key"]]["label"]
        collected_symptoms = [symptom_label]

        return {
            "response_text": response_text,
            "risk_level": risk_level,
            "clinical_handover": response_text,
            "step_number": total_steps,
            "total_steps": total_steps,
            "collected_symptoms": collected_symptoms,
            "answers": session["answers"]
        }
    except Exception as e:
        logger.exception("Clinical reasoning failed: %s", e)
        total_steps = len(session["required_questions"])
        symptom_label = SYMPTOM_LIBRARY[session["symptom_key"]]["label"]
        return {
            "response_text": "Clinical assessment completed. Please follow up with your doctor.",
            "risk_level": "Routine Medical Review 🟡",
            "clinical_handover": "Assessment completed.",
            "step_number": total_steps,
            "total_steps": total_steps,
            "collected_symptoms": [symptom_label],
            "answers": session.get("answers", {})
        }


from sqlalchemy.orm import Session
from app.db import models

def auto_extract_and_update_health_record(db: Session, user_id: str, query: str):
    """Parses, validates, and stores biometric vital signs from conversations."""
    query_lower = query.lower()
    
    # 1. Extract Blood Pressure (e.g. 120/80 or 120 over 80)
    bp_match = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})', query_lower)
    if not bp_match:
        bp_match = re.search(r'(\d{2,3})\s+over\s+(\d{2,3})', query_lower)
    
    # 2. Extract blood sugar / glucose (e.g. sugar 95 or glucose 110)
    glucose_match = re.search(r'(?:sugar|glucose|sugar level|sugar readings?)\s*(?:is|of|was|)?\s*(\d{2,3})', query_lower)
    
    # 3. Extract weight (e.g. weight 72 kg or log weight 70)
    weight_match = re.search(r'(?:weight|weight gain)\s*(?:is|of|was|)?\s*(\d{2,3})\s*(?:kg|lbs|pounds)?', query_lower)

    # 4. Extract temperature (e.g. temperature 98.6 or temp 100)
    temp_match = re.search(r'(?:temp|temperature)\s*(?:is|of|was|)?\s*(\d{2,3}(?:\.\d)?)\s*(?:c|f|degree)?', query_lower)

    # 5. Extract SpO2 (e.g. oxygen 98% or spo2 95)
    spo2_match = re.search(r'(?:oxygen|spo2|oxygen saturation)\s*(?:is|of|was|)?\s*(\d{2,3})\s*%?', query_lower)

    # 6. Extract Heart Rate (e.g. pulse 80 or heart rate 85)
    hr_match = re.search(r'(?:pulse|heart rate|bpm)\s*(?:is|of|was|)?\s*(\d{2,3})', query_lower)

    if bp_match or glucose_match or weight_match or temp_match or spo2_match or hr_match:
        from app.routes.ai import _get_or_create_twin
        twin = _get_or_create_twin(db, user_id)
        updated = False
        
        if bp_match:
            systolic = float(bp_match.group(1))
            diastolic = float(bp_match.group(2))
            # Validate BP range
            if 70 <= systolic <= 220 and 40 <= diastolic <= 130:
                twin.systolic_bp = systolic
                twin.diastolic_bp = diastolic
                updated = True
                logger.info(f"Validated BP: {systolic}/{diastolic}")
                
        if glucose_match:
            glucose = float(glucose_match.group(1))
            # Validate glucose range
            if 30 <= glucose <= 400:
                twin.glucose_level = glucose
                updated = True
                logger.info(f"Validated glucose: {glucose}")
                
        if weight_match:
            weight = float(weight_match.group(1))
            if 30 <= weight <= 200:
                if not twin.biomarkers:
                    twin.biomarkers = {}
                weight_logs = twin.biomarkers.get("weight_logs", [])
                weight_logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "weight": weight
                })
                twin.biomarkers["weight_logs"] = weight_logs
                updated = True
                logger.info(f"Validated weight: {weight}")

        if temp_match:
            temp = float(temp_match.group(1))
            # Convert Celsius to Fahrenheit if needed
            if 35.0 <= temp <= 42.0:
                temp = (temp * 9/5) + 32  # Celsius to Fahrenheit
            if 94.0 <= temp <= 106.0:
                twin.body_temp = temp
                updated = True
                logger.info(f"Validated body temp: {temp}")

        if spo2_match:
            spo2 = float(spo2_match.group(1))
            if 50 <= spo2 <= 100:
                if not twin.biomarkers:
                    twin.biomarkers = {}
                twin.biomarkers["spo2"] = spo2
                updated = True
                logger.info(f"Validated SpO2: {spo2}")

        if hr_match:
            hr = float(hr_match.group(1))
            if 40 <= hr <= 200:
                twin.heart_rate = hr
                updated = True
                logger.info(f"Validated heart rate: {hr}")
                
        if updated:
            try:
                db.add(twin)
                db.commit()
                # Run the risk calculation engine automatically
                from app.services.risk_engine import MaternalRiskEngine
                engine = MaternalRiskEngine()
                engine.evaluate_twin(db, user_id)
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to auto-update digital twin vitals: {e}")

    # 7. Extract medicine reminder (e.g. remind me to take folic acid at 8 AM)
    reminder_match = re.search(r'(?:remind|reminder|set reminder)\s*(?:me|for|to take|)?\s*([a-zA-Z\s]{3,30})\s*(?:at|every)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm|am\.|pm\.|))', query_lower)
    if reminder_match:
        med_name = reminder_match.group(1).strip()
        med_time = reminder_match.group(2).strip()
        
        for clean_word in ["to take", "to", "take", "for", "my"]:
            med_name = re.sub(rf'\b{clean_word}\b', '', med_name).strip()
            
        new_reminder = models.MedicineReminder(
            id=str(uuid.uuid4()),
            patient_id=user_id,
            medicine_name=med_name.title(),
            dosage="As directed",
            frequency="Daily",
            reminder_times=[med_time],
            start_date=datetime.utcnow(),
            source="self_added",
            is_active=True
        )
        try:
            db.add(new_reminder)
            db.commit()
            logger.info(f"Auto-created reminder for {med_name} at {med_time}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to auto-create reminder: {e}")
