import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from pathlib import Path

def generate_synthetic_data(num_samples=1000):
    # Features: [bp_sys, bp_dia, glucose, hb, bmi, week]
    np.random.seed(42)
    bp_sys = np.random.normal(120, 15, num_samples)
    bp_dia = np.random.normal(80, 10, num_samples)
    glucose = np.random.normal(90, 20, num_samples)
    hb = np.random.normal(12, 1.5, num_samples)
    bmi = np.random.normal(25, 5, num_samples)
    week = np.random.uniform(0, 40, num_samples)

    X = np.column_stack([bp_sys, bp_dia, glucose, hb, bmi, week])

    # Labels (0: Low Risk, 1: High Risk)
    # Pre-eclampsia
    y_pe = ((bp_sys >= 140) | (bp_dia >= 90) | ((bp_sys >= 130) & (bmi >= 30))).astype(int)
    # Gestational Diabetes
    y_gd = ((glucose >= 140) | ((glucose >= 110) & (bmi >= 30))).astype(int)
    # Anaemia
    y_an = (hb < 11.0).astype(int)

    return X, y_pe, y_gd, y_an

def train_and_save_model():
    print("Generating synthetic maternal health data...")
    X, y_pe, y_gd, y_an = generate_synthetic_data(5000)

    print("Training Pre-eclampsia model...")
    clf_pe = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    clf_pe.fit(X, y_pe)

    print("Training Gestational Diabetes model...")
    clf_gd = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    clf_gd.fit(X, y_gd)

    print("Training Anaemia model...")
    clf_an = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    clf_an.fit(X, y_an)

    # Save models
    models_dir = Path(__file__).resolve().parent.parent / "app" / "ml"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = models_dir / "risk_model.pkl"
    joblib.dump({"pe": clf_pe, "gd": clf_gd, "an": clf_an}, model_path)
    print(f"Models successfully saved to {model_path}")

if __name__ == "__main__":
    train_and_save_model()
