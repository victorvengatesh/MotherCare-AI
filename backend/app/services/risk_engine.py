"""
Maternal Risk Prediction Engine

Performs rule-based + weighted risk scoring for:
  - Pre-eclampsia
  - Gestational Diabetes
  - Anaemia

Each risk returns a 0–1 probability with a human-readable insight.
"""
import logging

logger = logging.getLogger("risk-engine")

import joblib
from pathlib import Path
import numpy as np

# Load ML models
models_path = Path(__file__).resolve().parent.parent / "ml" / "risk_model.pkl"
try:
    models = joblib.load(models_path)
    ml_pe = models["pe"]
    ml_gd = models["gd"]
    ml_an = models["an"]
    logger.info("Loaded ML risk models successfully.")
except Exception as e:
    logger.warning("Failed to load ML models. Falling back to rule-based scoring: %s", e)
    ml_pe = ml_gd = ml_an = None

class MaternalRiskEngine:

    # Thresholds (clinically grounded)
    BP_HIGH        = 140   # systolic mmHg
    BP_ELEVATED    = 130
    GLUCOSE_HIGH   = 140   # mg/dL
    GLUCOSE_BORDER = 110
    HB_LOW         = 11.0  # g/dL
    HB_BORDER      = 12.0
    BMI_OBESE      = 30.0
    BMI_OVERWEIGHT = 25.0
    AGE_RISK       = 35    # advanced maternal age

    def predict_risks(self, twin_data: dict) -> dict:
        """
        Input : dict of biomarker key-value pairs from DigitalTwin
        Output: { risk_scores: {...}, insights: [...], overall_risk: str }
        """
        bp_sys   = float(twin_data.get("systolic_bp",  120))
        bp_dia   = float(twin_data.get("diastolic_bp",  80))
        glucose  = float(twin_data.get("glucose_level",  90))
        hb       = float(twin_data.get("hemoglobin",    12))
        bmi      = float(twin_data.get("bmi",           22))
        week     = float(twin_data.get("current_week",   0))

        risks    = {}
        insights = []

        # ── Pre-eclampsia ────────────────────────────────────────────────────
        pe_score = 0.0
        if ml_pe is not None:
            features = np.array([[bp_sys, bp_dia, glucose, hb, bmi, week]])
            pe_score = float(ml_pe.predict_proba(features)[0][1])
            if pe_score > 0.5:
                insights.append(f"ML Model detected elevated Pre-eclampsia risk based on multidimensional markers.")
        else:
            if bp_sys >= self.BP_HIGH:
                pe_score += 0.65
            elif bp_sys >= self.BP_ELEVATED:
                pe_score += 0.30
            if bp_dia >= 90:
                pe_score += 0.20
            if bmi >= self.BMI_OBESE:
                pe_score += 0.10
            if week >= 20:
                pe_score += 0.05
        
        # Clinical Rule Overrides / Insights
        if bp_sys >= self.BP_HIGH:
            insights.append("Systolic BP ≥ 140 mmHg is a primary driver for pre-eclampsia risk.")
        elif bp_sys >= self.BP_ELEVATED:
            insights.append("Elevated systolic BP (130–139 mmHg) detected — monitor closely.")
        if bp_dia >= 90:
            insights.append("Diastolic BP ≥ 90 mmHg adds to cardiovascular risk.")

        risks["pre_eclampsia"] = round(min(max(pe_score, 0.0), 0.99), 2)

        # ── Gestational Diabetes ─────────────────────────────────────────────
        gd_score = 0.0
        if ml_gd is not None:
            features = np.array([[bp_sys, bp_dia, glucose, hb, bmi, week]])
            gd_score = float(ml_gd.predict_proba(features)[0][1])
            if gd_score > 0.5:
                insights.append(f"ML Model detected elevated Gestational Diabetes risk.")
        else:
            if glucose >= self.GLUCOSE_HIGH:
                gd_score += 0.65
            elif glucose >= self.GLUCOSE_BORDER:
                gd_score += 0.30
            if bmi >= self.BMI_OBESE:
                gd_score += 0.15
            elif bmi >= self.BMI_OVERWEIGHT:
                gd_score += 0.05
        
        if glucose >= self.GLUCOSE_HIGH:
            insights.append("Fasting glucose ≥ 140 mg/dL strongly indicates gestational diabetes risk.")
        elif glucose >= self.GLUCOSE_BORDER:
            insights.append("Borderline glucose (110–139 mg/dL) — dietary control recommended.")
        if bmi >= self.BMI_OBESE:
            insights.append("BMI ≥ 30 is an independent risk factor for gestational diabetes.")

        risks["gestational_diabetes"] = round(min(max(gd_score, 0.0), 0.99), 2)

        # ── Anaemia ──────────────────────────────────────────────────────────
        an_score = 0.0
        if ml_an is not None:
            features = np.array([[bp_sys, bp_dia, glucose, hb, bmi, week]])
            an_score = float(ml_an.predict_proba(features)[0][1])
            if an_score > 0.5:
                insights.append(f"ML Model detected elevated Anaemia risk.")
        else:
            if hb < self.HB_LOW:
                an_score += 0.75
            elif hb < self.HB_BORDER:
                an_score += 0.35
                
        if hb < self.HB_LOW:
            insights.append(f"Haemoglobin {hb} g/dL is below 11 — moderate to severe anaemia likely.")
        elif hb < self.HB_BORDER:
            insights.append(f"Haemoglobin {hb} g/dL is below normal — mild anaemia, consider iron supplementation.")

        risks["anemia"] = round(min(max(an_score, 0.0), 0.99), 2)

        # ── Overall risk level ───────────────────────────────────────────────
        max_risk = max(risks.values(), default=0)
        if max_risk >= 0.65:
            overall = "High"
        elif max_risk >= 0.30:
            overall = "Moderate"
        else:
            overall = "Low"

        if not insights:
            insights.append("All measured biomarkers are within normal reference ranges.")

        return {
            "risk_scores": risks,
            "insights": insights,
            "overall_risk": overall,
        }
