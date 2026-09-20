"""
Inference module for Engineering Student Performance Prediction.
File: ml/predict.py
"""

import os
import sys
import joblib
import pandas as pd
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.preprocess import NUMERICAL_FEATURES, CATEGORICAL_FEATURES, TARGET_CLASSES
from services.risk_engine import calculate_student_risk
from services.intervention_engine import generate_interventions

MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "student_performance_model.pkl")
_CACHED_ARTIFACT = None

def get_model():
    """
    Loads and caches the trained ML pipeline.
    """
    global _CACHED_ARTIFACT
    if _CACHED_ARTIFACT is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Trained model artifact not found at {MODEL_PATH}. "
                "Please run python ml/train_model.py first."
            )
        _CACHED_ARTIFACT = joblib.load(MODEL_PATH)
    return _CACHED_ARTIFACT

def extract_student_indicators(student_data, predicted_category):
    """
    Extracts key model indicators tailored to this student record.
    Uses cautious phrasing ('Important model indicators') rather than causal claims.
    """
    indicators = []
    
    # 1. Arrears / Backlogs indicator
    backlogs = int(student_data.get("backlogs", student_data.get("arrears", 0)))
    if backlogs > 0:
        indicators.append({
            "indicator": "Standing Arrears",
            "value": f"{backlogs} subjects",
            "status": "warning" if backlogs == 1 else "danger",
            "note": "Active standing arrears requiring remedial coaching & re-examination"
        })
    else:
        indicators.append({
            "indicator": "Arrear Standing",
            "value": "0 (All Clear)",
            "status": "success",
            "note": "All Clear academic status without standing arrears"
        })
        
    # 2. Attendance indicator
    att = float(student_data.get("attendance_percentage", 80))
    if att < 75.0:
        indicators.append({
            "indicator": "Class Attendance",
            "value": f"{att:.1f}%",
            "status": "danger" if att < 65.0 else "warning",
            "note": "Below minimum regulatory 75% attendance threshold"
        })
    else:
        indicators.append({
            "indicator": "Class Attendance",
            "value": f"{att:.1f}%",
            "status": "success",
            "note": "Satisfactory attendance compliance"
        })
        
    # 3. Previous Semester Standing (CGPA)
    prev = float(student_data.get("previous_semester_percentage", 70))
    cgpa = round(prev / 9.5, 2)
    indicators.append({
        "indicator": "Prev Sem CGPA",
        "value": f"{cgpa} / 10 ({prev:.1f}%)",
        "status": "danger" if cgpa < 5.8 else ("warning" if cgpa < 6.8 else "success"),
        "note": "Key historical baseline indicator in predictive model"
    })
    
    # 4. Internal Assessment Marks 1 & 2
    int1 = float(student_data.get("internal_exam_1", 60))
    int2 = float(student_data.get("internal_exam_2", 60))
    int_avg = (int1 + int2) / 2.0
    indicators.append({
        "indicator": "Internal Assessment Marks (1 & 2)",
        "value": f"IA1: {int1:.1f} | IA2: {int2:.1f} (Avg: {int_avg:.1f})",
        "status": "danger" if int_avg < 50 else ("warning" if int_avg < 65 else "success"),
        "note": "Continuous internal assessment splits driving performance category"
    })
    
    # 5. Laboratory & Practical Assessment
    lab = float(student_data.get("lab_score", 70))
    indicators.append({
        "indicator": "Practical / Lab Proficiency",
        "value": f"{lab:.1f}/100",
        "status": "danger" if lab < 50 else ("warning" if lab < 65 else "success"),
        "note": "Core hands-on engineering lab benchmark"
    })
    
    # 6. Project & Technical competence
    proj = float(student_data.get("project_score", 70))
    indicators.append({
        "indicator": "Capstone / Project Score",
        "value": f"{proj:.1f}/100",
        "status": "warning" if proj < 55 else "success",
        "note": "Hands-on engineering problem solving and project capability"
    })
    
    return indicators

def predict_student_performance(student_dict):
    """
    Performs end-to-end ML prediction, risk scoring, indicator extraction,
    and early intervention recommendation for a given engineering student.
    
    Parameters:
    - student_dict: dict containing student attributes
    
    Returns:
    - dict containing:
      - predicted_category: 'High' | 'Average' | 'Low'
      - confidence: float (0.0 to 100.0)
      - probabilities: dict of class -> probability
      - risk_level: 'HIGH RISK' | 'MEDIUM RISK' | 'LOW RISK'
      - risk_score: int
      - risk_factors: list
      - indicators: list of important model indicators
      - interventions: list of recommended early interventions
    """
    model_artifact = get_model()
    pipeline = model_artifact["pipeline"]
    model_name = model_artifact["model_name"]
    classes = list(model_artifact["classes"])
    
    # Clean and standardize student dict
    cleaned_dict = dict(student_dict)
    
    # 1. Handle missing study_hours_per_day safely (default to healthy 4.0 hrs)
    if "study_hours_per_day" not in cleaned_dict or cleaned_dict["study_hours_per_day"] is None or str(cleaned_dict["study_hours_per_day"]).strip() == "":
        cleaned_dict["study_hours_per_day"] = 4.0
    else:
        try:
            cleaned_dict["study_hours_per_day"] = float(cleaned_dict["study_hours_per_day"])
        except (ValueError, TypeError):
            cleaned_dict["study_hours_per_day"] = 4.0

    # 2. Handle Prev Sem CGPA conversion (if prev_sem_cgpa provided or previous_semester_percentage <= 10)
    if "prev_sem_cgpa" in cleaned_dict and cleaned_dict["prev_sem_cgpa"] not in (None, ""):
        try:
            cgpa_val = float(cleaned_dict["prev_sem_cgpa"])
            if cgpa_val <= 10.0:
                cleaned_dict["previous_semester_percentage"] = min(100.0, round(cgpa_val * 9.5, 1))
            else:
                cleaned_dict["previous_semester_percentage"] = cgpa_val
        except (ValueError, TypeError):
            pass
    elif "previous_semester_percentage" in cleaned_dict:
        try:
            p_val = float(cleaned_dict["previous_semester_percentage"])
            if p_val <= 10.0:
                cleaned_dict["previous_semester_percentage"] = min(100.0, round(p_val * 9.5, 1))
        except (ValueError, TypeError):
            pass
            
    # 3. Handle missing midterm_score gracefully (compute from Internal Assessments 1 & 2)
    if "midterm_score" not in cleaned_dict or cleaned_dict["midterm_score"] is None or str(cleaned_dict["midterm_score"]).strip() == "":
        ia1 = float(cleaned_dict.get("internal_exam_1", 65.0)) if cleaned_dict.get("internal_exam_1") not in (None, "") else 65.0
        ia2 = float(cleaned_dict.get("internal_exam_2", 65.0)) if cleaned_dict.get("internal_exam_2") not in (None, "") else 65.0
        cleaned_dict["midterm_score"] = round((ia1 + ia2) / 2.0, 1)
    else:
        try:
            cleaned_dict["midterm_score"] = float(cleaned_dict["midterm_score"])
        except (ValueError, TypeError):
            ia1 = float(cleaned_dict.get("internal_exam_1", 65.0)) if cleaned_dict.get("internal_exam_1") not in (None, "") else 65.0
            ia2 = float(cleaned_dict.get("internal_exam_2", 65.0)) if cleaned_dict.get("internal_exam_2") not in (None, "") else 65.0
            cleaned_dict["midterm_score"] = round((ia1 + ia2) / 2.0, 1)

    # Convert input dict to 1-row DataFrame ensuring all pipeline features exist
    df_input = pd.DataFrame([cleaned_dict])
    for col in NUMERICAL_FEATURES:
        if col not in df_input.columns or pd.isna(df_input[col].iloc[0]):
            if col == "study_hours_per_day":
                df_input[col] = 4.0
            elif col == "midterm_score":
                ia1 = float(cleaned_dict.get("internal_exam_1", 65.0))
                ia2 = float(cleaned_dict.get("internal_exam_2", 65.0))
                df_input[col] = round((ia1 + ia2) / 2.0, 1)
            else:
                df_input[col] = 50.0
    for col in CATEGORICAL_FEATURES:
        if col not in df_input.columns or pd.isna(df_input[col].iloc[0]):
            df_input[col] = "Computer Science and Engineering" if col == "department" else "Male"
    
    # Generate prediction
    pred_raw = pipeline.predict(df_input)[0]
    
    # Generate prediction probabilities
    if hasattr(pipeline, "predict_proba"):
        probs_arr = pipeline.predict_proba(df_input)[0]
        # Map pipeline classes to probabilities
        pipe_classes = list(pipeline.classes_)
        prob_dict = {}
        for c in classes:
            if c in pipe_classes:
                idx = pipe_classes.index(c)
                prob_dict[c] = round(float(probs_arr[idx]), 4)
            else:
                prob_dict[c] = 0.0
                
        # Confidence is probability of predicted class
        conf = float(prob_dict.get(pred_raw, max(probs_arr))) * 100.0
    else:
        prob_dict = {c: (1.0 if c == pred_raw else 0.0) for c in classes}
        conf = 100.0
        
    # Calculate transparent risk
    risk_info = calculate_student_risk(cleaned_dict, predicted_category=pred_raw)
    
    # Extract important indicators (cautious, transparent wording)
    indicators = extract_student_indicators(cleaned_dict, predicted_category=pred_raw)
    
    # Generate early interventions
    interventions = generate_interventions(
        cleaned_dict,
        predicted_category=pred_raw,
        risk_level=risk_info["risk_level"]
    )
    
    student_id = cleaned_dict.get("student_id", "N/A")
    name = cleaned_dict.get("name", f"Student {student_id}")
    parent_email = cleaned_dict.get("parent_email", f"parent.{student_id.lower()}@example.edu")
    prev_pct = float(cleaned_dict.get("previous_semester_percentage", 70.0))
    prev_cgpa = round(prev_pct / 9.5, 2)
    
    return {
        "student_id": student_id,
        "name": name,
        "parent_email": parent_email,
        "prev_sem_cgpa": prev_cgpa,
        "previous_semester_percentage": prev_pct,
        "predicted_category": pred_raw,
        "confidence": round(conf, 1),
        "probabilities": prob_dict,
        "model_used": model_name,
        "risk_level": risk_info["risk_level"],
        "risk_score": risk_info["risk_score"],
        "risk_color": risk_info["risk_color"],
        "risk_factors": risk_info["risk_factors"],
        "indicators": indicators,
        "interventions": interventions
    }
