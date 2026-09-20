"""
Main Flask Application.
AI-Based Engineering Student Performance Prediction and Early Intervention System
File: app.py
"""

import os
import sys
import io
import csv
import json
from functools import wraps
from datetime import datetime

import pandas as pd
from sqlalchemy import or_
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify, Response
)

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import Config
from database.models import db, User, Student, Prediction, Intervention
from database.database import init_db
from ml.predict import predict_student_performance
from ml.preprocess import TARGET_CLASSES, CATEGORICAL_FEATURES, NUMERICAL_FEATURES
from services.risk_engine import calculate_student_risk
from services.intervention_engine import generate_interventions
from services.email_service import generate_parent_email_content, dispatch_parent_email
from services.analytics import (
    get_dashboard_kpis,
    get_dashboard_charts,
    get_student_profile_charts,
    get_model_performance_charts
)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize database
    db.init_app(app)
    
    # Context processor to expose logged in user and roles to all templates
    @app.context_processor
    def inject_user():
        current_user = None
        if "user_id" in session:
            current_user = db.session.get(User, session["user_id"])
        return {
            "current_user": current_user,
            "now": datetime.utcnow()
        }
        
    # Authentication helpers
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login", next=request.url))
            return f(*args, **kwargs)
        return decorated_function

    def role_required(*roles):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if "user_id" not in session:
                    flash("Please log in first.", "warning")
                    return redirect(url_for("login"))
                user_role = session.get("role", "")
                if user_role not in roles and "admin" not in roles:
                    if user_role == "student" and session.get("student_id"):
                        flash("Students are authorized to access their personal academic portal only.", "warning")
                        return redirect(url_for("student_detail", student_id=session.get("student_id")))
                    flash("You do not have permission to access that resource.", "danger")
                    return redirect(url_for("dashboard"))
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    # ------------------ Routes ------------------ #

    @app.route("/")
    @app.route("/api")
    @app.route("/api/")
    @app.route("/api/index")
    @app.route("/api/index.py")
    def index():
        if "user_id" in session:
            if session.get("role") == "student" and session.get("student_id"):
                return redirect(url_for("student_detail", student_id=session.get("student_id")))
            return redirect(url_for("dashboard"))
        return login()

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if "user_id" in session:
            if session.get("role") == "student" and session.get("student_id"):
                return redirect(url_for("student_detail", student_id=session.get("student_id")))
            return redirect(url_for("dashboard"))
            
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            
            if not username or not password:
                flash("Please provide both unique ID / username and password.", "danger")
                return render_template("login.html")
                
            # 1. Try matching existing User account
            user = User.query.filter(User.username.ilike(username)).first()
            if user and user.check_password(password):
                session["user_id"] = user.id
                session["username"] = user.username
                session["role"] = user.role
                session["student_id"] = user.student_id
                flash(f"Welcome back, {user.username} ({user.role.title()})!", "success")
                
                if user.role == "student" and user.student_id:
                    return redirect(url_for("student_detail", student_id=user.student_id))
                    
                next_page = request.args.get("next")
                return redirect(next_page if next_page else url_for("dashboard"))
                
            # 2. Try matching Unique Student ID directly for student authentication
            student = Student.query.filter(Student.student_id.ilike(username)).first()
            if student:
                # Accept standard student password or student ID
                if password in ["student123", student.student_id, student.student_id.lower()]:
                    if not user:
                        user = User(username=student.student_id, role="student", student_id=student.student_id)
                        user.set_password(password)
                        db.session.add(user)
                        db.session.commit()
                        
                    session["user_id"] = user.id
                    session["username"] = user.username
                    session["role"] = "student"
                    session["student_id"] = student.student_id
                    flash(f"Welcome to your Academic Portal, {student.name} ({student.student_id})!", "success")
                    return redirect(url_for("student_detail", student_id=student.student_id))
                    
            flash("Invalid username or password. For student login, use your unique Student ID (e.g., ENG0001) and student123.", "danger")
                
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been successfully logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    @role_required("admin", "faculty")
    def dashboard():
        if session.get("role") == "student" and session.get("student_id"):
            return redirect(url_for("student_detail", student_id=session.get("student_id")))
            
        kpis = get_dashboard_kpis()
        charts = get_dashboard_charts()
        
        # Recent at-risk students preview
        at_risk_preview = Student.query.filter(
            (Student.latest_risk_level == "HIGH RISK") | (Student.backlogs >= 2)
        ).order_by(Student.attendance_percentage.asc()).limit(8).all()
        
        return render_template(
            "dashboard.html",
            kpis=kpis,
            charts=charts,
            at_risk_preview=at_risk_preview
        )

    @app.route("/search")
    @login_required
    def search():
        # Students can only search or see their own record
        if session.get("role") == "student" and session.get("student_id"):
            return redirect(url_for("student_detail", student_id=session.get("student_id")))

        q = request.args.get("q", "").strip()
        if not q:
            return redirect(url_for("students"))
            
        matches = Student.query.filter(
            or_(
                Student.student_id.ilike(f"%{q}%"),
                Student.name.ilike(f"%{q}%")
            )
        ).all()
        
        if len(matches) == 1:
            return redirect(url_for("student_detail", student_id=matches[0].student_id))
            
        departments = [d[0] for d in db.session.query(Student.department).distinct().order_by(Student.department).all()]
        return render_template(
            "students.html",
            students=matches,
            departments=departments,
            search_query=q,
            current_dept="",
            current_sem="",
            current_risk="",
            current_perf=""
        )

    @app.route("/students")
    @login_required
    @role_required("admin", "faculty")
    def students():
        if session.get("role") == "student" and session.get("student_id"):
            return redirect(url_for("student_detail", student_id=session.get("student_id")))

        # Filters
        dept_filter = request.args.get("department", "")
        sem_filter = request.args.get("semester", "")
        risk_filter = request.args.get("risk_level", "")
        perf_filter = request.args.get("performance", "")
        search_query = request.args.get("search", "").strip()
        page = request.args.get("page", 1, type=int)
        per_page = 20
        
        query = Student.query
        
        if dept_filter:
            query = query.filter(Student.department == dept_filter)
        if sem_filter:
            query = query.filter(Student.semester == int(sem_filter))
        if risk_filter:
            query = query.filter(Student.latest_risk_level == risk_filter)
        if perf_filter:
            query = query.filter(Student.latest_prediction == perf_filter)
        if search_query:
            query = query.filter(
                or_(
                    Student.student_id.ilike(f"%{search_query}%"),
                    Student.name.ilike(f"%{search_query}%"),
                    Student.department.ilike(f"%{search_query}%")
                )
            )
            
        pagination = query.order_by(Student.student_id.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        departments = [d[0] for d in db.session.query(Student.department).distinct().order_by(Student.department).all()]
        
        return render_template(
            "students.html",
            students=pagination.items,
            pagination=pagination,
            departments=departments,
            current_dept=dept_filter,
            current_sem=sem_filter,
            current_risk=risk_filter,
            current_perf=perf_filter,
            search_query=search_query
        )

    @app.route("/student/<student_id>")
    @login_required
    def student_detail(student_id):
        # Security: student role can only view their own record
        if session.get("role") == "student" and session.get("student_id") != student_id:
            flash("You are authorized to view your own academic profile only.", "danger")
            return redirect(url_for("student_detail", student_id=session.get("student_id")))
            
        student = Student.query.filter_by(student_id=student_id).first_or_404()
        
        # Get charts for this student
        profile_charts = get_student_profile_charts(student)
        
        # Get historical predictions
        predictions = Prediction.query.filter_by(student_id=student_id).order_by(Prediction.created_at.desc()).all()
        
        # Parse indicators for the latest prediction
        latest_indicators = []
        if predictions and predictions[0].important_indicators:
            try:
                latest_indicators = json.loads(predictions[0].important_indicators)
            except Exception:
                pass
                
        # Interventions history
        interventions = Intervention.query.filter_by(student_id=student_id).order_by(Intervention.created_at.desc()).all()
        
        # Generate fresh real-time interventions
        student_dict = student.to_dict()
        fresh_interventions = generate_interventions(
            student_dict,
            predicted_category=student.latest_prediction or "Average",
            risk_level=student.latest_risk_level or "LOW RISK"
        )
        
        # Risk factors
        risk_data = calculate_student_risk(student_dict, predicted_category=student.latest_prediction or "Average")
        
        return render_template(
            "student_detail.html",
            student=student,
            charts=profile_charts,
            predictions=predictions,
            latest_indicators=latest_indicators,
            interventions=interventions,
            fresh_interventions=fresh_interventions,
            risk_data=risk_data
        )

    @app.route("/student/<student_id>/send-parent-email", methods=["POST"])
    @login_required
    def send_parent_email(student_id):
        if session.get("role") not in ["admin", "faculty"]:
            flash("Only faculty or administrative mentors can send official parent reports.", "danger")
            return redirect(url_for("student_detail", student_id=student_id))
            
        student = Student.query.filter_by(student_id=student_id).first_or_404()
        override_email = request.form.get("parent_email", "").strip()
        if override_email:
            student.parent_email = override_email
            db.session.commit()
            
        target_email = student.parent_email or f"parent.{student.student_id.lower()}@college.edu"
        email_content = generate_parent_email_content(student)
        success, msg = dispatch_parent_email(target_email, email_content)
        
        # Log this intervention in database
        interv = Intervention(
            student_id=student.student_id,
            risk_level=student.latest_risk_level or "LOW RISK",
            recommendation=f"Parent Academic Notification dispatched to {target_email}",
            action_taken=f"Official AI prediction & academic standing summary emailed to parent ({target_email}).",
            status="In Progress",
            created_at=datetime.utcnow()
        )
        db.session.add(interv)
        db.session.commit()
        
        flash(f"Academic prediction report successfully sent to parent's email: {target_email}!", "success")
        return redirect(request.referrer or url_for("student_detail", student_id=student_id))

    @app.route("/student/<student_id>/download-report")
    @login_required
    def download_student_report(student_id):
        if session.get("role") == "student" and session.get("student_id") != student_id:
            flash("Unauthorized.", "danger")
            return redirect(url_for("student_detail", student_id=session.get("student_id")))
            
        student = Student.query.filter_by(student_id=student_id).first_or_404()
        prev_cgpa = round(student.previous_semester_percentage / 9.5, 2)
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["=" * 60])
        writer.writerow(["ENGINEERING STUDENT PERFORMANCE & AI PREDICTION REPORT"])
        writer.writerow(["=" * 60])
        writer.writerow([])
        writer.writerow(["STUDENT PROFILE"])
        writer.writerow(["Unique Student ID", student.student_id])
        writer.writerow(["Student Name", student.name])
        writer.writerow(["Parent Contact Email", student.parent_email])
        writer.writerow(["Department", student.department])
        writer.writerow(["Semester", student.semester])
        writer.writerow(["Gender", student.gender])
        writer.writerow(["Age", student.age])
        writer.writerow([])
        writer.writerow(["CONTINUOUS ACADEMIC ASSESSMENTS"])
        writer.writerow(["Class Attendance", f"{student.attendance_percentage}%"])
        writer.writerow(["Prev Sem CGPA (0 - 10)", prev_cgpa])
        writer.writerow(["Previous Semester %", f"{student.previous_semester_percentage}%"])
        writer.writerow(["Internal Assessment 1 Marks", student.internal_exam_1])
        writer.writerow(["Internal Assessment 2 Marks", student.internal_exam_2])
        writer.writerow(["Midterm Exam Score", student.midterm_score])
        writer.writerow(["Assignment Average", student.assignment_average])
        writer.writerow(["Lab / Practical Score", student.lab_score])
        writer.writerow(["Project / Capstone Score", student.project_score])
        writer.writerow(["Active Backlogs", student.backlogs])
        writer.writerow(["Previous Failures", student.previous_failures])
        writer.writerow([])
        writer.writerow(["AI PREDICTION & RISK DIAGNOSTICS"])
        writer.writerow(["Projected Outcome Category", student.latest_prediction or "Average"])
        writer.writerow(["Risk Classification", student.latest_risk_level or "LOW RISK"])
        writer.writerow(["Model Confidence", f"{student.latest_confidence or 85.0}%"])
        writer.writerow([])
        writer.writerow(["Report Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
        writer.writerow(["Issuing Platform", "EduVision AI Student Performance Management System"])
        
        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=Academic_Report_{student.student_id}.csv"}
        )

    @app.route("/student/<student_id>/edit", methods=["GET", "POST"])
    @login_required
    @role_required("admin", "faculty")
    def edit_student(student_id):
        student = Student.query.filter_by(student_id=student_id).first_or_404()
        
        if request.method == "POST":
            try:
                # 1. Update basic profile info
                student.name = request.form.get("name", student.name).strip()
                student.parent_email = request.form.get("parent_email", student.parent_email).strip()
                student.department = request.form.get("department", student.department).strip()
                student.semester = int(request.form.get("semester", student.semester))
                student.age = int(request.form.get("age", student.age))
                student.gender = request.form.get("gender", student.gender).strip()
                
                # 2. Update continuous academic assessments
                student.internal_exam_1 = float(request.form.get("internal_exam_1", student.internal_exam_1))
                student.internal_exam_2 = float(request.form.get("internal_exam_2", student.internal_exam_2))
                # Auto-calculate continuous internal assessment / midterm score
                student.midterm_score = round((student.internal_exam_1 + student.internal_exam_2) / 2.0, 1)
                
                student.assignment_average = float(request.form.get("assignment_average", student.assignment_average))
                student.lab_score = float(request.form.get("lab_score", student.lab_score))
                student.project_score = float(request.form.get("project_score", student.project_score))
                student.attendance_percentage = float(request.form.get("attendance_percentage", student.attendance_percentage))
                
                # Previous sem CGPA (0 - 10)
                if request.form.get("prev_sem_cgpa"):
                    student.prev_sem_cgpa = float(request.form.get("prev_sem_cgpa"))
                elif request.form.get("previous_semester_percentage"):
                    student.previous_semester_percentage = float(request.form.get("previous_semester_percentage"))
                    
                student.study_hours_per_day = float(request.form.get("study_hours_per_day", student.study_hours_per_day or 4.0))
                student.class_participation = int(request.form.get("class_participation", student.class_participation or 5))
                student.extracurricular_score = float(request.form.get("extracurricular_score", student.extracurricular_score or 50.0))
                
                # 3. Update academic arrear section
                student.backlogs = int(request.form.get("backlogs", student.backlogs))
                student.previous_failures = int(request.form.get("previous_failures", student.previous_failures))
                
                # 4. Update engineering skills
                student.technical_skill_score = float(request.form.get("technical_skill_score", student.technical_skill_score))
                student.coding_skill_score = float(request.form.get("coding_skill_score", student.coding_skill_score))
                student.communication_skill_score = float(request.form.get("communication_skill_score", student.communication_skill_score))
                student.aptitude_score = float(request.form.get("aptitude_score", student.aptitude_score))
                
                # 5. Re-run ML prediction to update student's risk level and category
                pred = predict_student_performance(student.to_dict())
                student.latest_prediction = pred.get("predicted_category", student.latest_prediction)
                student.latest_risk_level = pred.get("risk_level", student.latest_risk_level)
                student.latest_confidence = pred.get("confidence", student.latest_confidence)
                
                db.session.commit()
                flash(f"Student {student.name} ({student.student_id}) profile and assessment marks successfully updated!", "success")
                return redirect(url_for("student_detail", student_id=student.student_id))
                
            except Exception as e:
                db.session.rollback()
                flash(f"Error updating student: {str(e)}", "danger")
                
        departments = [
            "Computer Science & Engineering",
            "Information Technology",
            "Electronics & Communication Engineering",
            "Mechanical Engineering",
            "Civil Engineering",
            "Electrical & Electronics Engineering",
            "Artificial Intelligence & Data Science"
        ]
        return render_template("edit_student.html", student=student, departments=departments)

    @app.route("/student/<student_id>/delete", methods=["POST"])
    @login_required
    @role_required("admin", "faculty")
    def delete_student(student_id):
        student = Student.query.filter_by(student_id=student_id).first_or_404()
        student_name = student.name or f"Student {student.student_id}"
        
        try:
            # 1. Delete associated student login user if exists
            User.query.filter_by(student_id=student.student_id).delete()
            
            # 2. Delete student record (cascades to predictions and interventions)
            db.session.delete(student)
            db.session.commit()
            
            flash(f"Student profile for {student_name} ({student_id}) has been permanently removed.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting student {student_id}: {str(e)}", "danger")
            
        return redirect(url_for("students"))

    @app.route("/import-csv", methods=["GET", "POST"])
    @login_required
    @role_required("admin", "faculty")
    def import_csv():
        if request.method == "POST":
            if "csv_file" not in request.files:
                flash("No file was uploaded.", "danger")
                return redirect(url_for("import_csv"))
                
            file = request.files["csv_file"]
            if file.filename == "":
                flash("Please choose a valid CSV file to upload.", "danger")
                return redirect(url_for("import_csv"))
                
            if not file.filename.lower().endswith(".csv"):
                flash("Invalid format. Please upload a standard comma-separated .csv file.", "danger")
                return redirect(url_for("import_csv"))
                
            try:
                df = pd.read_csv(file)
                if "student_id" not in df.columns:
                    flash("Invalid CSV schema: 'student_id' column is required.", "danger")
                    return redirect(url_for("import_csv"))
                    
                imported_count = 0
                updated_count = 0
                
                for _, row in df.iterrows():
                    st_id = str(row["student_id"]).strip().upper()
                    if not st_id or st_id.lower() == "nan":
                        continue
                        
                    row_dict = row.to_dict()
                    
                    # Handle CGPA to % conversion
                    prev_cgpa = row_dict.get("prev_sem_cgpa")
                    prev_pct = row_dict.get("previous_semester_percentage")
                    if prev_cgpa not in (None, "") and not pd.isna(prev_cgpa):
                        c_val = float(prev_cgpa)
                        calc_pct = min(100.0, round(c_val * 9.5, 1)) if c_val <= 10.0 else c_val
                    elif prev_pct not in (None, "") and not pd.isna(prev_pct):
                        p_val = float(prev_pct)
                        calc_pct = min(100.0, round(p_val * 9.5, 1)) if p_val <= 10.0 else p_val
                    else:
                        calc_pct = 72.0
                        
                    student_payload = {
                        "student_id": st_id,
                        "name": str(row_dict.get("name", f"Student {st_id}")).strip(),
                        "parent_email": str(row_dict.get("parent_email", f"parent.{st_id.lower()}@college.edu")).strip(),
                        "department": str(row_dict.get("department", "Computer Science and Engineering")).strip(),
                        "semester": int(row_dict.get("semester", 5)) if not pd.isna(row_dict.get("semester")) else 5,
                        "age": int(row_dict.get("age", 20)) if not pd.isna(row_dict.get("age")) else 20,
                        "gender": str(row_dict.get("gender", "Male")).strip(),
                        "attendance_percentage": float(row_dict.get("attendance_percentage", 75.0)) if not pd.isna(row_dict.get("attendance_percentage")) else 75.0,
                        "study_hours_per_day": 4.0,
                        "previous_semester_percentage": calc_pct,
                        "internal_exam_1": float(row_dict.get("internal_exam_1", 65.0)) if not pd.isna(row_dict.get("internal_exam_1")) else 65.0,
                        "internal_exam_2": float(row_dict.get("internal_exam_2", 65.0)) if not pd.isna(row_dict.get("internal_exam_2")) else 65.0,
                        "assignment_average": float(row_dict.get("assignment_average", 70.0)) if not pd.isna(row_dict.get("assignment_average")) else 70.0,
                        "lab_score": float(row_dict.get("lab_score", 70.0)) if not pd.isna(row_dict.get("lab_score")) else 70.0,
                        "midterm_score": float(row_dict.get("midterm_score", 65.0)) if not pd.isna(row_dict.get("midterm_score")) else 65.0,
                        "project_score": float(row_dict.get("project_score", 65.0)) if not pd.isna(row_dict.get("project_score")) else 65.0,
                        "backlogs": int(row_dict.get("backlogs", 0)) if not pd.isna(row_dict.get("backlogs")) else 0,
                        "previous_failures": int(row_dict.get("previous_failures", 0)) if not pd.isna(row_dict.get("previous_failures")) else 0,
                        "class_participation": int(row_dict.get("class_participation", 6)) if not pd.isna(row_dict.get("class_participation")) else 6,
                        "extracurricular_score": float(row_dict.get("extracurricular_score", 50.0)) if not pd.isna(row_dict.get("extracurricular_score")) else 50.0,
                        "technical_skill_score": float(row_dict.get("technical_skill_score", 65.0)) if not pd.isna(row_dict.get("technical_skill_score")) else 65.0,
                        "coding_skill_score": float(row_dict.get("coding_skill_score", 60.0)) if not pd.isna(row_dict.get("coding_skill_score")) else 60.0,
                        "communication_skill_score": float(row_dict.get("communication_skill_score", 65.0)) if not pd.isna(row_dict.get("communication_skill_score")) else 65.0,
                        "aptitude_score": float(row_dict.get("aptitude_score", 65.0)) if not pd.isna(row_dict.get("aptitude_score")) else 65.0,
                    }
                    
                    # Run AI prediction
                    pred_res = predict_student_performance(student_payload)
                    
                    existing_st = Student.query.filter_by(student_id=st_id).first()
                    if existing_st:
                        for k, v in student_payload.items():
                            setattr(existing_st, k, v)
                        existing_st.latest_prediction = pred_res["predicted_category"]
                        existing_st.latest_risk_level = pred_res["risk_level"]
                        existing_st.latest_confidence = pred_res["confidence"]
                        updated_count += 1
                    else:
                        new_student = Student(**student_payload)
                        new_student.latest_prediction = pred_res["predicted_category"]
                        new_student.latest_risk_level = pred_res["risk_level"]
                        new_student.latest_confidence = pred_res["confidence"]
                        db.session.add(new_student)
                        imported_count += 1
                        
                    # Save prediction record
                    pred_rec = Prediction(
                        student_id=st_id,
                        prediction=pred_res["predicted_category"],
                        risk_level=pred_res["risk_level"],
                        prediction_probability=pred_res["confidence"],
                        important_indicators=json.dumps(pred_res["indicators"]),
                        model_name=pred_res["model_used"]
                    )
                    db.session.add(pred_rec)
                    
                db.session.commit()
                flash(f"CSV Ingestion Complete! Added {imported_count} new student(s), updated {updated_count} student(s), and executed real-time AI predictions.", "success")
                return redirect(url_for("students"))
            except Exception as e:
                db.session.rollback()
                flash(f"Failed to process CSV: {str(e)}", "danger")
                return redirect(url_for("import_csv"))
                
        return render_template("import_csv.html")

    @app.route("/download-sample-csv")
    @login_required
    @role_required("admin", "faculty")
    def download_sample_csv():
        sample_rows = [
            ["student_id", "name", "parent_email", "department", "semester", "age", "gender", "attendance_percentage", "prev_sem_cgpa", "internal_exam_1", "internal_exam_2", "assignment_average", "lab_score", "technical_skill_score", "coding_skill_score", "communication_skill_score", "aptitude_score", "backlogs", "previous_failures", "class_participation", "extracurricular_score", "project_score", "midterm_score"],
            ["ENG2001", "Aarav Sharma", "parent.aarav@college.edu", "Computer Science and Engineering", 5, 20, "Male", 88.5, 8.4, 78.0, 82.5, 85.0, 80.0, 78.0, 85.0, 75.0, 80.0, 0, 0, 8, 65.0, 82.0, 76.0],
            ["ENG2002", "Priya Patel", "parent.priya@college.edu", "Information Technology", 5, 20, "Female", 68.0, 6.2, 54.0, 58.0, 62.0, 65.0, 60.0, 62.0, 68.0, 65.0, 2, 1, 5, 45.0, 60.0, 55.0],
            ["ENG2003", "Karthik Iyer", "parent.karthik@college.edu", "Electronics and Communication Engineering", 6, 21, "Male", 92.0, 9.1, 88.0, 90.0, 90.0, 88.0, 85.0, 80.0, 82.0, 88.0, 0, 0, 9, 80.0, 88.0, 85.0],
            ["ENG2004", "Sneha Reddy", "parent.sneha@college.edu", "Electrical and Electronics Engineering", 4, 19, "Female", 74.0, 7.0, 64.0, 62.0, 70.0, 72.0, 68.0, 65.0, 72.0, 70.0, 0, 0, 6, 50.0, 70.0, 65.0],
            ["ENG2005", "Vikram Singh", "parent.vikram@college.edu", "Mechanical Engineering", 6, 21, "Male", 62.5, 5.8, 48.0, 52.0, 58.0, 60.0, 55.0, 50.0, 65.0, 60.0, 3, 2, 4, 40.0, 58.0, 50.0]
        ]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(sample_rows)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=sample_students_template.csv"}
        )

    @app.route("/predict", methods=["GET", "POST"])
    @login_required
    def predict():
        if session.get("role") == "student" and session.get("student_id"):
            return redirect(url_for("student_detail", student_id=session.get("student_id")))

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
        
        if request.method == "POST":
            try:
                student_id = request.form.get("student_id", "").strip().upper()
                if not student_id:
                    student_id = f"ENG{datetime.utcnow().strftime('%H%M%S')}"
                    
                student_name = request.form.get("name", "").strip() or f"Student {student_id}"
                parent_email = request.form.get("parent_email", "").strip() or f"parent.{student_id.lower()}@college.edu"
                
                # Prev Sem CGPA to Percentage conversion
                prev_cgpa_str = request.form.get("prev_sem_cgpa", "").strip()
                if prev_cgpa_str:
                    cgpa_val = float(prev_cgpa_str)
                    prev_pct = min(100.0, round(cgpa_val * 9.5, 1)) if cgpa_val <= 10.0 else cgpa_val
                else:
                    prev_pct = float(request.form.get("previous_semester_percentage", 70.0))
                    
                input_data = {
                    "student_id": student_id,
                    "name": student_name,
                    "parent_email": parent_email,
                    "department": request.form.get("department"),
                    "semester": int(request.form.get("semester", 5)),
                    "age": int(request.form.get("age", 20)),
                    "gender": request.form.get("gender", "Male"),
                    "attendance_percentage": float(request.form.get("attendance_percentage", 75.0)),
                    "study_hours_per_day": 4.0, # Study hours removed from form, defaulted in backend
                    "previous_semester_percentage": prev_pct,
                    "prev_sem_cgpa": round(prev_pct / 9.5, 2),
                    "internal_exam_1": float(request.form.get("internal_exam_1", 60.0)),
                    "internal_exam_2": float(request.form.get("internal_exam_2", 60.0)),
                    "assignment_average": float(request.form.get("assignment_average", 70.0)),
                    "lab_score": float(request.form.get("lab_score", 70.0)),
                    "technical_skill_score": float(request.form.get("technical_skill_score", 65.0)),
                    "coding_skill_score": float(request.form.get("coding_skill_score", 60.0)),
                    "communication_skill_score": float(request.form.get("communication_skill_score", 65.0)),
                    "aptitude_score": float(request.form.get("aptitude_score", 65.0)),
                    "backlogs": int(request.form.get("backlogs", 0)),
                    "previous_failures": int(request.form.get("previous_failures", 0)),
                    "class_participation": int(request.form.get("class_participation", 6)),
                    "extracurricular_score": float(request.form.get("extracurricular_score", 50.0)),
                    "project_score": float(request.form.get("project_score", 65.0)),
                    "midterm_score": float(request.form.get("midterm_score")) if request.form.get("midterm_score") not in (None, "") else round((float(request.form.get("internal_exam_1", 60.0)) + float(request.form.get("internal_exam_2", 60.0))) / 2.0, 1)
                }
                
                # Perform real-time ML prediction & risk classification
                result = predict_student_performance(input_data)
                
                # Check if student exists in database; if not or update, persist
                existing_student = Student.query.filter_by(student_id=student_id).first()
                db_fields = {k: v for k, v in input_data.items() if k in Student.__table__.columns.keys()}
                if existing_student:
                    for k, v in db_fields.items():
                        setattr(existing_student, k, v)
                    existing_student.latest_prediction = result["predicted_category"]
                    existing_student.latest_risk_level = result["risk_level"]
                    existing_student.latest_confidence = result["confidence"]
                else:
                    new_student = Student(**db_fields)
                    new_student.latest_prediction = result["predicted_category"]
                    new_student.latest_risk_level = result["risk_level"]
                    new_student.latest_confidence = result["confidence"]
                    db.session.add(new_student)
                    
                # Save prediction record
                pred_record = Prediction(
                    student_id=student_id,
                    prediction=result["predicted_category"],
                    risk_level=result["risk_level"],
                    prediction_probability=result["confidence"],
                    important_indicators=json.dumps(result["indicators"]),
                    model_name=result["model_used"]
                )
                db.session.add(pred_record)
                db.session.commit()
                
                flash(f"Performance prediction computed successfully for {student_name} ({student_id}).", "success")
                return render_template(
                    "prediction.html",
                    result=result,
                    input_data=input_data,
                    departments=departments
                )
                
            except Exception as e:
                db.session.rollback()
                flash(f"Error executing prediction: {str(e)}", "danger")
                return render_template("prediction.html", departments=departments)
                
        return render_template("prediction.html", departments=departments)

    @app.route("/api/predict", methods=["POST"])
    def api_predict():
        """RESTful API endpoint for programmatic inference."""
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({"error": "No JSON payload provided"}), 400
                
            result = predict_student_performance(data)
            return jsonify({
                "status": "success",
                "data": result
            }), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/at-risk")
    @login_required
    @role_required("admin", "faculty")
    def at_risk():
        if session.get("role") == "student" and session.get("student_id"):
            return redirect(url_for("student_detail", student_id=session.get("student_id")))

        dept_filter = request.args.get("department", "")
        risk_filter = request.args.get("risk_level", "HIGH RISK")
        
        query = Student.query
        
        if risk_filter == "ALL":
            query = query.filter((Student.latest_risk_level == "HIGH RISK") | (Student.latest_risk_level == "MEDIUM RISK"))
        elif risk_filter:
            query = query.filter(Student.latest_risk_level == risk_filter)
            
        if dept_filter:
            query = query.filter(Student.department == dept_filter)
            
        students_list = query.order_by(Student.attendance_percentage.asc()).all()
        departments = [d[0] for d in db.session.query(Student.department).distinct().order_by(Student.department).all()]
        
        return render_template(
            "at_risk.html",
            students=students_list,
            departments=departments,
            current_dept=dept_filter,
            current_risk=risk_filter
        )

    @app.route("/interventions", methods=["GET", "POST"])
    @login_required
    @role_required("admin", "faculty")
    def interventions():
        if session.get("role") == "student" and session.get("student_id"):
            return redirect(url_for("student_detail", student_id=session.get("student_id")))

        if request.method == "POST":
            student_id = request.form.get("student_id", "").strip().upper()
            student = Student.query.filter_by(student_id=student_id).first()
            if not student:
                flash(f"Student ID {student_id} not found in database.", "danger")
                return redirect(url_for("interventions"))
                
            recommendation = request.form.get("recommendation", "").strip()
            faculty_note = request.form.get("faculty_note", "").strip()
            action_taken = request.form.get("action_taken", "").strip()
            status = request.form.get("status", "Pending")
            follow_up_date = request.form.get("follow_up_date", "")
            
            interv = Intervention(
                student_id=student_id,
                risk_level=student.latest_risk_level or "MEDIUM RISK",
                recommendation=recommendation,
                faculty_note=faculty_note,
                action_taken=action_taken,
                status=status,
                follow_up_date=follow_up_date
            )
            db.session.add(interv)
            db.session.commit()
            flash(f"Intervention recorded successfully for {student_id}.", "success")
            return redirect(url_for("interventions"))
            
        status_filter = request.args.get("status", "")
        search_query = request.args.get("search", "").strip()
        
        query = Intervention.query.join(Student)
        if status_filter:
            query = query.filter(Intervention.status == status_filter)
        if search_query:
            query = query.filter(
                or_(
                    Intervention.student_id.ilike(f"%{search_query}%"),
                    Student.name.ilike(f"%{search_query}%")
                )
            )
            
        records = query.order_by(Intervention.created_at.desc()).all()
        
        pending_count = Intervention.query.filter_by(status="Pending").count()
        in_progress_count = Intervention.query.filter_by(status="In Progress").count()
        completed_count = Intervention.query.filter_by(status="Completed").count()
        
        return render_template(
            "interventions.html",
            interventions=records,
            pending_count=pending_count,
            in_progress_count=in_progress_count,
            completed_count=completed_count,
            current_status=status_filter,
            search_query=search_query
        )

    @app.route("/interventions/<int:id>/update", methods=["POST"])
    @login_required
    @role_required("admin", "faculty")
    def update_intervention(id):
        interv = Intervention.query.get_or_404(id)
        interv.status = request.form.get("status", interv.status)
        interv.faculty_note = request.form.get("faculty_note", interv.faculty_note)
        interv.action_taken = request.form.get("action_taken", interv.action_taken)
        interv.follow_up_date = request.form.get("follow_up_date", interv.follow_up_date)
        interv.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Intervention for {interv.student_id} updated to '{interv.status}'.", "success")
        return redirect(request.referrer or url_for("interventions"))

    @app.route("/model-performance")
    @login_required
    @role_required("admin", "faculty")
    def model_performance():
        metrics_file = app.config["METRICS_PATH"]
        if not os.path.exists(metrics_file):
            flash("Model metrics not found. Please train models first using python ml/train_model.py.", "warning")
            return render_template("model_performance.html", metrics=None, charts={})
            
        with open(metrics_file, "r") as f:
            metrics_data = json.load(f)
            
        charts = get_model_performance_charts(metrics_data)
        
        return render_template(
            "model_performance.html",
            metrics=metrics_data,
            charts=charts
        )

    return app

# Application entrypoint
app = create_app()

if __name__ == "__main__":
    init_db(app)
    print("\n* AI-Based Engineering Student Performance Prediction & Early Intervention System")
    print("* Application running on: http://127.0.0.1:5000")
    print("* Default logins: admin/admin123, faculty/faculty123, student/student123 (or Student ID e.g. ENG0001)\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
