"""
SQLAlchemy ORM models for Engineering Student Performance System.
File: database/models.py
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="faculty") # 'admin', 'faculty', 'student'
    student_id = db.Column(db.String(20), nullable=True) # Linked student ID if role == 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "student_id": self.student_id,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }

class Student(db.Model):
    __tablename__ = "students"
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=True, default="Student")
    parent_email = db.Column(db.String(120), nullable=True)
    department = db.Column(db.String(100), nullable=False, index=True)
    semester = db.Column(db.Integer, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    
    # Academic attributes
    attendance_percentage = db.Column(db.Float, nullable=False)
    study_hours_per_day = db.Column(db.Float, nullable=False, default=4.0)
    previous_semester_percentage = db.Column(db.Float, nullable=False)
    internal_exam_1 = db.Column(db.Float, nullable=False)
    internal_exam_2 = db.Column(db.Float, nullable=False)
    assignment_average = db.Column(db.Float, nullable=False)
    lab_score = db.Column(db.Float, nullable=False)
    midterm_score = db.Column(db.Float, nullable=False)
    project_score = db.Column(db.Float, nullable=False)
    backlogs = db.Column(db.Integer, nullable=False, default=0)
    previous_failures = db.Column(db.Integer, nullable=False, default=0)
    class_participation = db.Column(db.Integer, nullable=False, default=5)
    extracurricular_score = db.Column(db.Float, nullable=False, default=50.0)
    
    # Skill attributes
    technical_skill_score = db.Column(db.Float, nullable=False)
    coding_skill_score = db.Column(db.Float, nullable=False)
    communication_skill_score = db.Column(db.Float, nullable=False)
    aptitude_score = db.Column(db.Float, nullable=False)
    
    # Historical / ground-truth benchmark
    final_exam_score = db.Column(db.Float, nullable=True)
    performance_category = db.Column(db.String(20), nullable=True)
    
    # Latest cached prediction state
    latest_prediction = db.Column(db.String(20), nullable=True)
    latest_risk_level = db.Column(db.String(20), nullable=True)
    latest_confidence = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    predictions = db.relationship("Prediction", backref="student_ref", lazy=True, cascade="all, delete-orphan")
    interventions = db.relationship("Intervention", backref="student_ref", lazy=True, cascade="all, delete-orphan")
    
    # Convenience properties & setters
    @property
    def arrears(self):
        return self.backlogs

    @arrears.setter
    def arrears(self, val):
        self.backlogs = int(val) if val is not None else 0

    @property
    def arrears_count(self):
        return self.backlogs

    @arrears_count.setter
    def arrears_count(self, val):
        self.backlogs = int(val) if val is not None else 0

    @property
    def prev_sem_cgpa(self):
        return round(self.previous_semester_percentage / 9.5, 2) if self.previous_semester_percentage else 0.0

    @prev_sem_cgpa.setter
    def prev_sem_cgpa(self, val):
        if val not in (None, ""):
            v = float(val)
            self.previous_semester_percentage = round(v * 9.5, 1) if v <= 10.0 else v

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name or f"Student {self.student_id}",
            "parent_email": self.parent_email or f"parent.{self.student_id.lower()}@example.edu",
            "department": self.department,
            "semester": self.semester,
            "age": self.age,
            "gender": self.gender,
            "attendance_percentage": self.attendance_percentage,
            "study_hours_per_day": self.study_hours_per_day,
            "previous_semester_percentage": self.previous_semester_percentage,
            "prev_sem_cgpa": round(self.previous_semester_percentage / 9.5, 2) if self.previous_semester_percentage else 0.0,
            "internal_exam_1": self.internal_exam_1,
            "internal_exam_2": self.internal_exam_2,
            "assignment_average": self.assignment_average,
            "lab_score": self.lab_score,
            "midterm_score": self.midterm_score,
            "project_score": self.project_score,
            "backlogs": self.backlogs,
            "arrears": self.backlogs,
            "arrears_count": self.backlogs,
            "previous_failures": self.previous_failures,
            "history_of_arrears": self.previous_failures,
            "class_participation": self.class_participation,
            "extracurricular_score": self.extracurricular_score,
            "technical_skill_score": self.technical_skill_score,
            "coding_skill_score": self.coding_skill_score,
            "communication_skill_score": self.communication_skill_score,
            "aptitude_score": self.aptitude_score,
            "final_exam_score": self.final_exam_score,
            "performance_category": self.performance_category,
            "latest_prediction": self.latest_prediction,
            "latest_risk_level": self.latest_risk_level,
            "latest_confidence": self.latest_confidence
        }

class Prediction(db.Model):
    __tablename__ = "predictions"
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey("students.student_id"), nullable=False, index=True)
    prediction = db.Column(db.String(20), nullable=False) # 'High', 'Average', 'Low'
    risk_level = db.Column(db.String(20), nullable=False) # 'LOW RISK', 'MEDIUM RISK', 'HIGH RISK'
    prediction_probability = db.Column(db.Float, nullable=False)
    important_indicators = db.Column(db.Text, nullable=True) # JSON serialized string
    model_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "prediction": self.prediction,
            "risk_level": self.risk_level,
            "prediction_probability": self.prediction_probability,
            "important_indicators": self.important_indicators,
            "model_name": self.model_name,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }

class Intervention(db.Model):
    __tablename__ = "interventions"
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey("students.student_id"), nullable=False, index=True)
    risk_level = db.Column(db.String(20), nullable=False)
    recommendation = db.Column(db.Text, nullable=False)
    faculty_note = db.Column(db.Text, nullable=True)
    action_taken = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending") # 'Pending', 'In Progress', 'Completed'
    follow_up_date = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "risk_level": self.risk_level,
            "recommendation": self.recommendation,
            "faculty_note": self.faculty_note,
            "action_taken": self.action_taken,
            "status": self.status,
            "follow_up_date": self.follow_up_date,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None
        }
