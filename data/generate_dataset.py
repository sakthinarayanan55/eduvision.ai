"""
Generate realistic synthetic dataset for Engineering Student Performance Prediction.
File: data/generate_dataset.py
Output: data/engineering_student_performance.csv

Features avoid target leakage by explicitly excluding final_exam_score from training features.
All records are fully anonymized with IDs: ENG0001, ENG0002, etc.
"""

import os
import numpy as np
import pandas as pd

def generate_dataset(num_records=1250, seed=42):
    np.random.seed(seed)
    
    departments = [
        "Computer Science and Engineering",
        "Information Technology",
        "Electronics and Communication Engineering",
        "Electrical and Electronics Engineering",
        "Mechanical Engineering",
        "Civil Engineering",
        "Artificial Intelligence and Data Science",
        "Artificial Intelligence and Machine Learning"
    ]
    
    dept_weights = [0.18, 0.14, 0.14, 0.12, 0.12, 0.10, 0.10, 0.10]
    genders = ["Male", "Female", "Other"]
    gender_weights = [0.58, 0.40, 0.02]
    
    records = []
    
    for i in range(1, num_records + 1):
        student_id = f"ENG{i:04d}"
        dept = np.random.choice(departments, p=dept_weights)
        semester = int(np.random.choice([3, 4, 5, 6, 7, 8], p=[0.15, 0.20, 0.25, 0.20, 0.12, 0.08]))
        age = int(np.random.choice([19, 20, 21, 22, 23], p=[0.15, 0.35, 0.35, 0.12, 0.03]))
        gender = np.random.choice(genders, p=gender_weights)
        
        # Latent academic capability factor: between 0.3 and 1.0 (mean ~0.65)
        # to ensure realistic inter-feature correlation
        latent_ability = np.clip(np.random.beta(5, 3), 0.2, 0.98)
        effort_factor = np.clip(np.random.beta(4, 3), 0.15, 0.98)
        
        # Attendance percentage (typical range 55% to 98%)
        base_att = 50 + 48 * (0.6 * effort_factor + 0.4 * np.random.rand())
        attendance_percentage = round(float(np.clip(base_att, 45.0, 99.5)), 1)
        
        # Study hours per day (0.5 to 8.0 hrs)
        base_study = 1.0 + 6.5 * (0.7 * effort_factor + 0.3 * np.random.rand())
        study_hours_per_day = round(float(np.clip(base_study, 0.5, 8.0)), 1)
        
        # Previous semester percentage (40% to 96%)
        prev_sem = 40 + 56 * (0.7 * latent_ability + 0.3 * effort_factor + 0.1 * (np.random.rand() - 0.5))
        previous_semester_percentage = round(float(np.clip(prev_sem, 40.0, 98.0)), 1)
        
        # Internal exams (0 to 100)
        int1 = 35 + 60 * (0.65 * latent_ability + 0.25 * effort_factor + 0.1 * np.random.rand())
        internal_exam_1 = round(float(np.clip(int1, 25.0, 99.0)), 1)
        
        int2 = 0.5 * internal_exam_1 + 45 * (0.5 * latent_ability + 0.5 * effort_factor) + (np.random.rand() - 0.5) * 10
        internal_exam_2 = round(float(np.clip(int2, 25.0, 100.0)), 1)
        
        # Assignment average (40 to 100)
        assign = 45 + 52 * (0.8 * effort_factor + 0.2 * latent_ability + 0.05 * (np.random.rand() - 0.5))
        assignment_average = round(float(np.clip(assign, 40.0, 100.0)), 1)
        
        # Lab score
        lab = 45 + 50 * (0.5 * latent_ability + 0.4 * effort_factor + 0.1 * np.random.rand())
        lab_score = round(float(np.clip(lab, 40.0, 100.0)), 1)
        
        # Skill scores (0 to 100)
        is_cs_branch = dept in [
            "Computer Science and Engineering",
            "Information Technology",
            "Artificial Intelligence and Data Science",
            "Artificial Intelligence and Machine Learning"
        ]
        
        cs_bonus = 8.0 if is_cs_branch else -5.0
        coding_skill = 35 + 55 * latent_ability + cs_bonus + (np.random.rand() - 0.5) * 15
        coding_skill_score = round(float(np.clip(coding_skill, 20.0, 98.0)), 1)
        
        tech = 35 + 58 * (0.6 * latent_ability + 0.4 * effort_factor) + (np.random.rand() - 0.5) * 10
        technical_skill_score = round(float(np.clip(tech, 25.0, 99.0)), 1)
        
        comm = 40 + 55 * np.random.beta(4, 3)
        communication_skill_score = round(float(np.clip(comm, 30.0, 98.0)), 1)
        
        apt = 35 + 60 * latent_ability + (np.random.rand() - 0.5) * 12
        aptitude_score = round(float(np.clip(apt, 25.0, 98.0)), 1)
        
        # Backlogs: inversely related to ability and effort
        risk_tendency = (1.0 - latent_ability) * 0.6 + (1.0 - effort_factor) * 0.4
        if risk_tendency > 0.65:
            backlogs = int(np.random.choice([1, 2, 3, 4], p=[0.4, 0.3, 0.2, 0.1]))
            previous_failures = backlogs + int(np.random.choice([0, 1, 2], p=[0.5, 0.35, 0.15]))
        elif risk_tendency > 0.45:
            backlogs = int(np.random.choice([0, 1, 2], p=[0.6, 0.3, 0.1]))
            previous_failures = backlogs + int(np.random.choice([0, 1], p=[0.75, 0.25]))
        else:
            backlogs = 0
            previous_failures = int(np.random.choice([0, 1], p=[0.92, 0.08]))
            
        # Class participation (1 to 10)
        part = 1 + 9 * (0.6 * effort_factor + 0.4 * (attendance_percentage / 100))
        class_participation = int(np.clip(round(part), 1, 10))
        
        # Extracurricular score (1 to 100)
        extracurricular_score = round(float(np.random.uniform(20.0, 95.0)), 1)
        
        # Project score (30 to 100)
        proj = 40 + 55 * (0.5 * latent_ability + 0.3 * effort_factor + 0.2 * (technical_skill_score / 100))
        project_score = round(float(np.clip(proj, 35.0, 99.0)), 1)
        
        # Midterm score (30 to 100)
        mid = 0.5 * internal_exam_1 + 0.5 * internal_exam_2 + (np.random.rand() - 0.5) * 8
        midterm_score = round(float(np.clip(mid, 28.0, 99.0)), 1)
        
        # Ground-truth Final Exam Score calculation (incorporates actual academic performance)
        final_score = (
            0.22 * previous_semester_percentage +
            0.18 * internal_exam_1 +
            0.18 * internal_exam_2 +
            0.10 * assignment_average +
            0.10 * lab_score +
            0.08 * midterm_score +
            0.07 * (attendance_percentage * 0.8) +
            0.07 * technical_skill_score -
            (backlogs * 3.5) +
            (np.random.normal(0, 3.0))
        )
        final_exam_score = round(float(np.clip(final_score, 25.0, 99.0)), 1)
        
        # Documented, reproducible rule for performance category:
        # High: final_exam_score >= 75.0 (or top-tier cumulative work)
        # Average: 55.0 <= final_exam_score < 75.0
        # Low: final_exam_score < 55.0 or backlogs >= 2
        if final_exam_score >= 74.0 and backlogs == 0:
            performance_category = "High"
        elif final_exam_score < 56.0 or backlogs >= 2:
            performance_category = "Low"
        else:
            performance_category = "Average"
            
        records.append({
            "student_id": student_id,
            "department": dept,
            "semester": semester,
            "age": age,
            "gender": gender,
            "attendance_percentage": attendance_percentage,
            "study_hours_per_day": study_hours_per_day,
            "previous_semester_percentage": previous_semester_percentage,
            "internal_exam_1": internal_exam_1,
            "internal_exam_2": internal_exam_2,
            "assignment_average": assignment_average,
            "lab_score": lab_score,
            "technical_skill_score": technical_skill_score,
            "coding_skill_score": coding_skill_score,
            "communication_skill_score": communication_skill_score,
            "aptitude_score": aptitude_score,
            "backlogs": backlogs,
            "previous_failures": previous_failures,
            "class_participation": class_participation,
            "extracurricular_score": extracurricular_score,
            "project_score": project_score,
            "midterm_score": midterm_score,
            "final_exam_score": final_exam_score,
            "performance_category": performance_category
        })
        
    df = pd.DataFrame(records)
    
    os.makedirs("data", exist_ok=True)
    csv_path = os.path.join("data", "engineering_student_performance.csv")
    df.to_csv(csv_path, index=False)
    print(f"Dataset generated successfully at {csv_path} with {len(df)} records.")
    print("Class distribution:")
    print(df["performance_category"].value_counts())
    print("\nDepartment distribution:")
    print(df["department"].value_counts())
    return csv_path

if __name__ == "__main__":
    generate_dataset()
