"""
Transparent Risk Engine for Engineering Students.
File: services/risk_engine.py

Calculates risk score (0-100) and classifies into:
- HIGH RISK
- MEDIUM RISK
- LOW RISK

Factors Evaluated:
1. ML Predicted Performance Category (High/Average/Low)
2. Attendance Percentage (Mandatory 75% university threshold)
3. Active Backlogs and Failures
4. Previous Semester Academic Percentage
5. Internal Assessment Average Marks
6. Daily Study Hours
7. Core Technical & Problem-Solving Skill Indicators
"""

def calculate_student_risk(student_data, predicted_category="Average"):
    """
    Computes a transparent risk score and risk level classification.
    
    Parameters:
    - student_data: dict or Series containing student features
    - predicted_category: str ('High', 'Average', 'Low')
    
    Returns:
    - dict containing:
      - risk_level: 'HIGH RISK' | 'MEDIUM RISK' | 'LOW RISK'
      - risk_score: int (0-100)
      - risk_factors: list of identified risk factor descriptions
      - risk_color: badge color code ('danger', 'warning', 'success')
    """
    risk_score = 0
    factors = []
    
    # 1. Model Prediction
    pred_upper = str(predicted_category).strip().title()
    if pred_upper == "Low":
        risk_score += 35
        factors.append("Model predicts 'Low' semester performance outcome")
    elif pred_upper == "Average":
        risk_score += 10
        
    # 2. Attendance (<75% triggers regulatory academic warning)
    attendance = float(student_data.get("attendance_percentage", 80))
    if attendance < 65.0:
        risk_score += 25
        factors.append(f"Critical attendance deficit: {attendance:.1f}% (<65% threshold)")
    elif attendance < 75.0:
        risk_score += 15
        factors.append(f"Sub-optimal attendance: {attendance:.1f}% (below 75% requirement)")
    elif attendance < 80.0:
        risk_score += 5

    # 3. Active Backlogs
    backlogs = int(student_data.get("backlogs", 0))
    if backlogs >= 3:
        risk_score += 30
        factors.append(f"Severe backlog accumulation: {backlogs} uncleared subjects")
    elif backlogs >= 1:
        risk_score += 15 * backlogs
        factors.append(f"Active backlogs present: {backlogs} subject(s)")
        
    # 4. Previous Academic Standing
    prev_sem = float(student_data.get("previous_semester_percentage", 70))
    if prev_sem < 50.0:
        risk_score += 15
        factors.append(f"Low prior academic standing: {prev_sem:.1f}%")
    elif prev_sem < 60.0:
        risk_score += 8
        factors.append(f"Marginal prior percentage: {prev_sem:.1f}%")
        
    # 5. Internal Assessment Average
    int1 = float(student_data.get("internal_exam_1", 60))
    int2 = float(student_data.get("internal_exam_2", 60))
    internal_avg = (int1 + int2) / 2.0
    if internal_avg < 50.0:
        risk_score += 15
        factors.append(f"Poor internal assessment performance: {internal_avg:.1f}/100 avg")
    elif internal_avg < 60.0:
        risk_score += 8
        
    # 6. Daily Study Hours
    study_hrs = float(student_data.get("study_hours_per_day", 3))
    if study_hrs < 1.5:
        risk_score += 10
        factors.append(f"Insufficient daily study dedication: {study_hrs:.1f} hrs/day")
    elif study_hrs < 2.5:
        risk_score += 5
        
    # 7. Core Skills
    coding = float(student_data.get("coding_skill_score", 60))
    tech = float(student_data.get("technical_skill_score", 60))
    min_skill = min(coding, tech)
    if min_skill < 45.0:
        risk_score += 10
        factors.append(f"Low core technical/coding assessment: {min_skill:.1f}/100")
    elif min_skill < 55.0:
        risk_score += 5
        
    # Clamp score to 100
    risk_score = min(100, risk_score)
    
    # Classification Decision Rules
    if risk_score >= 45 or backlogs >= 2 or (pred_upper == "Low" and attendance < 75.0):
        risk_level = "HIGH RISK"
        risk_color = "danger"
    elif risk_score >= 20 or backlogs == 1 or attendance < 75.0 or pred_upper == "Low":
        risk_level = "MEDIUM RISK"
        risk_color = "warning"
    else:
        risk_level = "LOW RISK"
        risk_color = "success"
        
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": factors if factors else ["Academic and attendance indicators are within healthy parameters."],
        "risk_color": risk_color
    }
