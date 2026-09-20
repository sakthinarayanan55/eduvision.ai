"""
Database initialization and seeding module.
File: database/database.py
"""

import os
import json
import pandas as pd
from database.models import db, User, Student, Prediction, Intervention
from ml.predict import predict_student_performance

def init_db(app):
    """Initializes the database schema with the Flask application context."""
    with app.app_context():
        db.create_all()
        seed_data(app)

def seed_data(app):
    """
    Seeds initial default administrative/faculty/student users
    and loads students from the generated dataset into SQLite.
    Computes initial ML predictions so the system is fully populated.
    """
    with app.app_context():
        # 1. Seed Users if not present
        if User.query.count() == 0:
            print("Seeding default authentication credentials...")
            admin_user = User(username="admin", role="admin")
            admin_user.set_password("admin123")
            
            faculty_user = User(username="faculty", role="faculty")
            faculty_user.set_password("faculty123")
            
            student_user = User(username="student", role="student", student_id="ENG0001")
            student_user.set_password("student123")
            
            db.session.add_all([admin_user, faculty_user, student_user])
            db.session.commit()
            print("Users seeded: admin (admin/admin123), faculty (faculty/faculty123), student (student/student123)")
            
        # 2. Seed Students if empty
        if Student.query.count() == 0:
            csv_path = os.path.join(app.root_path, "data", "engineering_student_performance.csv")
            if not os.path.exists(csv_path):
                print(f"Warning: CSV file not found at {csv_path}, skipping student seeding.")
                return
                
            print(f"Importing students from {csv_path}...")
            df = pd.read_csv(csv_path)
            
            students_to_add = []
            predictions_to_add = []
            interventions_to_add = []
            
            # Batch process students
            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                student = Student(
                    student_id=row_dict["student_id"],
                    name=row_dict.get("name", f"Student {row_dict['student_id']}"),
                    parent_email=row_dict.get("parent_email", f"parent.{row_dict['student_id'].lower()}@example.edu"),
                    department=row_dict["department"],
                    semester=int(row_dict["semester"]),
                    age=int(row_dict["age"]),
                    gender=row_dict["gender"],
                    attendance_percentage=float(row_dict["attendance_percentage"]),
                    study_hours_per_day=float(row_dict["study_hours_per_day"]),
                    previous_semester_percentage=float(row_dict["previous_semester_percentage"]),
                    internal_exam_1=float(row_dict["internal_exam_1"]),
                    internal_exam_2=float(row_dict["internal_exam_2"]),
                    assignment_average=float(row_dict["assignment_average"]),
                    lab_score=float(row_dict["lab_score"]),
                    midterm_score=float(row_dict["midterm_score"]),
                    project_score=float(row_dict["project_score"]),
                    backlogs=int(row_dict["backlogs"]),
                    previous_failures=int(row_dict["previous_failures"]),
                    class_participation=int(row_dict["class_participation"]),
                    extracurricular_score=float(row_dict["extracurricular_score"]),
                    technical_skill_score=float(row_dict["technical_skill_score"]),
                    coding_skill_score=float(row_dict["coding_skill_score"]),
                    communication_skill_score=float(row_dict["communication_skill_score"]),
                    aptitude_score=float(row_dict["aptitude_score"]),
                    final_exam_score=float(row_dict.get("final_exam_score", 0)),
                    performance_category=str(row_dict.get("performance_category", "Average"))
                )
                
                # Precompute ML prediction for initial state
                try:
                    res = predict_student_performance(row_dict)
                    student.latest_prediction = res["predicted_category"]
                    student.latest_risk_level = res["risk_level"]
                    student.latest_confidence = res["confidence"]
                    
                    # Also log prediction in table for sample records
                    if idx < 300: # Store initial prediction records
                        pred = Prediction(
                            student_id=student.student_id,
                            prediction=res["predicted_category"],
                            risk_level=res["risk_level"],
                            prediction_probability=res["confidence"],
                            important_indicators=json.dumps(res["indicators"]),
                            model_used=res["model_used"]
                        )
                        predictions_to_add.append(pred)
                        
                    # Create starter intervention for High Risk students
                    if res["risk_level"] == "HIGH RISK" and len(interventions_to_add) < 25:
                        recom_text = res["interventions"][0]["recommendation"] if res["interventions"] else "Attendance and backlog review needed."
                        interv = Intervention(
                            student_id=student.student_id,
                            risk_level=res["risk_level"],
                            recommendation=recom_text,
                            faculty_note="Scheduled initial advisory discussion with departmental mentor.",
                            action_taken="Mentor meeting conducted; revision timetable drafted.",
                            status="In Progress" if idx % 2 == 0 else "Pending",
                            follow_up_date="2026-10-15"
                        )
                        interventions_to_add.append(interv)
                except Exception as e:
                    pass
                    
                students_to_add.append(student)
                
            db.session.bulk_save_objects(students_to_add)
            db.session.commit()
            
            if predictions_to_add:
                db.session.bulk_save_objects(predictions_to_add)
            if interventions_to_add:
                db.session.bulk_save_objects(interventions_to_add)
            db.session.commit()
            print(f"Successfully seeded {len(students_to_add)} students into SQLite database.")
