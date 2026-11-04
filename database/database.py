"""
Database initialization and seeding module.
File: database/database.py
"""

import os
import json
import sqlite3
import pandas as pd
from database.models import db, User, Student, Prediction, Intervention
from ml.predict import predict_student_performance

def migrate_user_columns(app):
    """Ensures newly added user columns exist in SQLite database without losing data."""
    try:
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if "sqlite:///" in db_uri:
            db_path = db_uri.replace("sqlite:///", "")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                existing_cols = [row[1] for row in cursor.fetchall()]
                
                new_columns = [
                    ("full_name", "VARCHAR(120)"),
                    ("email", "VARCHAR(120)"),
                    ("department", "VARCHAR(100)"),
                    ("designation", "VARCHAR(100) DEFAULT 'Faculty Mentor'")
                ]
                
                for col_name, col_type in new_columns:
                    if col_name not in existing_cols:
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                
                conn.commit()
                conn.close()
    except Exception as e:
        print(f"User column migration note: {e}")

def init_db(app):
    """Initializes the database schema with the Flask application context."""
    with app.app_context():
        db.create_all()
        migrate_user_columns(app)
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
            admin_user = User(
                username="admin", 
                role="admin", 
                full_name="Chief Academic Administrator",
                email="admin@eduvision.edu",
                department="Academic Administration",
                designation="System Director"
            )
            admin_user.set_password("admin123")
            
            faculty_user = User(
                username="faculty", 
                role="faculty",
                full_name="Dr. Eleanor Vance",
                email="faculty@eduvision.edu",
                department="Computer Science",
                designation="Associate Professor & Academic Mentor"
            )
            faculty_user.set_password("faculty123")
            
            student_user = User(
                username="student", 
                role="student", 
                student_id="ENG0001",
                full_name="Aarav Sharma",
                email="aarav.sharma@eduvision.edu",
                department="Computer Science"
            )
            student_user.set_password("student123")
            
            db.session.add_all([admin_user, faculty_user, student_user])
            db.session.commit()
            print("Users seeded: admin (admin/admin123), faculty (faculty/faculty123), student (student/student123)")
        else:
            # Update existing faculty/admin records with default display names if missing
            admin_rec = User.query.filter_by(username="admin").first()
            if admin_rec and not admin_rec.full_name:
                admin_rec.full_name = "Chief Academic Administrator"
                admin_rec.email = "admin@eduvision.edu"
                admin_rec.department = "Academic Administration"
                admin_rec.designation = "System Director"
                
            fac_rec = User.query.filter_by(username="faculty").first()
            if fac_rec and not fac_rec.full_name:
                fac_rec.full_name = "Dr. Eleanor Vance"
                fac_rec.email = "faculty@eduvision.edu"
                fac_rec.department = "Computer Science"
                fac_rec.designation = "Associate Professor & Academic Mentor"
            db.session.commit()
            
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
                    parent_email=row_dict.get("parent_email", f"parent.{str(row_dict['student_id']).lower()}@example.edu"),
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
                    if idx < 60:
                        res = predict_student_performance(row_dict)
                        student.latest_prediction = res["predicted_category"]
                        student.latest_risk_level = res["risk_level"]
                        student.latest_confidence = res["confidence"]
                        
                        pred = Prediction(
                            student_id=student.student_id,
                            prediction=res["predicted_category"],
                            risk_level=res["risk_level"],
                            prediction_probability=res["confidence"],
                            important_indicators=json.dumps(res["indicators"]),
                            model_used=res["model_used"]
                        )
                        predictions_to_add.append(pred)
                        
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
                    else:
                        perf_cat = str(row_dict.get("performance_category", "Average"))
                        att = float(row_dict.get("attendance_percentage", 75.0))
                        backlogs = int(row_dict.get("backlogs", 0))
                        
                        if perf_cat == "Low" or backlogs >= 2 or att < 65.0:
                            risk_level = "HIGH RISK"
                            confidence = 0.88
                        elif perf_cat == "Average" or att < 75.0 or backlogs == 1:
                            risk_level = "MEDIUM RISK"
                            confidence = 0.84
                        else:
                            risk_level = "LOW RISK"
                            confidence = 0.92
                            
                        student.latest_prediction = perf_cat
                        student.latest_risk_level = risk_level
                        student.latest_confidence = confidence
                except Exception as e:
                    student.latest_prediction = str(row_dict.get("performance_category", "Average"))
                    student.latest_risk_level = "LOW RISK"
                    student.latest_confidence = 0.85
                    
                students_to_add.append(student)
                
            db.session.bulk_save_objects(students_to_add)
            db.session.commit()
            
            if predictions_to_add:
                db.session.bulk_save_objects(predictions_to_add)
            if interventions_to_add:
                db.session.bulk_save_objects(interventions_to_add)
            db.session.commit()
            print(f"Successfully seeded {len(students_to_add)} students into SQLite database.")
