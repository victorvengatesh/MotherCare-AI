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

class XGBoostModelStub:
    def predict(self, features):
        return 0.5

xgb_model = XGBoostModelStub()


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
        if bp_sys >= self.BP_HIGH:
            pe_score += 0.65
            insights.append("Systolic BP ≥ 140 mmHg is the primary driver for pre-eclampsia risk.")
        elif bp_sys >= self.BP_ELEVATED:
            pe_score += 0.30
            insights.append("Elevated systolic BP (130–139 mmHg) detected — monitor closely.")
        if bp_dia >= 90:
            pe_score += 0.20
            insights.append("Diastolic BP ≥ 90 mmHg adds to cardiovascular risk.")
        if bmi >= self.BMI_OBESE:
            pe_score += 0.10
        if week >= 20:
            pe_score += 0.05  # Risk increases in 2nd/3rd trimester
        risks["pre_eclampsia"] = round(min(pe_score, 0.99), 2)

        # ── Gestational Diabetes ─────────────────────────────────────────────
        gd_score = 0.0
        if glucose >= self.GLUCOSE_HIGH:
            gd_score += 0.65
            insights.append("Fasting glucose ≥ 140 mg/dL strongly indicates gestational diabetes risk.")
        elif glucose >= self.GLUCOSE_BORDER:
            gd_score += 0.30
            insights.append("Borderline glucose (110–139 mg/dL) — dietary control recommended.")
        if bmi >= self.BMI_OBESE:
            gd_score += 0.15
            insights.append("BMI ≥ 30 is an independent risk factor for gestational diabetes.")
        elif bmi >= self.BMI_OVERWEIGHT:
            gd_score += 0.05
        risks["gestational_diabetes"] = round(min(gd_score, 0.99), 2)

        # ── Anaemia ──────────────────────────────────────────────────────────
        an_score = 0.0
        if hb < self.HB_LOW:
            an_score += 0.75
            insights.append(f"Haemoglobin {hb} g/dL is below 11 — moderate to severe anaemia likely.")
        elif hb < self.HB_BORDER:
            an_score += 0.35
            insights.append(f"Haemoglobin {hb} g/dL is below normal — mild anaemia, consider iron supplementation.")
        risks["anemia"] = round(min(an_score, 0.99), 2)

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
