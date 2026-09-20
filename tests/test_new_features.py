"""
Integration tests for newly added features:
- Student Unique ID login and isolation
- Student Name and Parent Email
- Internal Assessment Marks 1 & 2
- Prev Sem CGPA
- Removal of Study Hours from prediction form
- Parent Email dispatch
- CSV Import and sample CSV download
- Search by Unique ID or Student Name
- Report Download
"""

import io
import unittest
from app import create_app
from database.models import db, Student, User, Intervention

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_student_unique_id_login_and_isolation(self):
        # Student logs in with unique ID ENG0001
        res = self.client.post("/login", data={
            "username": "ENG0001",
            "password": "student123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"ENG0001", res.data)
        
        # Student tries accessing admin dashboard - should be blocked and redirected
        dash_res = self.client.get("/dashboard", follow_redirects=True)
        self.assertIn(b"ENG0001", dash_res.data) # redirected to student_detail
        
        # Student tries accessing another student's page - should be blocked
        other_res = self.client.get("/student/ENG0002", follow_redirects=True)
        self.assertIn(b"authorized to view your own academic profile only", other_res.data)

    def test_admin_features_and_search(self):
        # Login as admin
        self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)

        # 1. Search by student ID
        res_id = self.client.get("/search?q=ENG0001", follow_redirects=True)
        self.assertEqual(res_id.status_code, 200)
        self.assertIn(b"ENG0001", res_id.data)

        # 2. Search by student name
        res_name = self.client.get("/search?q=Sharma", follow_redirects=True)
        self.assertEqual(res_name.status_code, 200)
        self.assertIn(b"Sharma", res_name.data)

        # 3. Download Sample CSV
        res_sample = self.client.get("/download-sample-csv")
        self.assertEqual(res_sample.status_code, 200)
        self.assertIn(b"prev_sem_cgpa", res_sample.data)
        self.assertIn(b"internal_exam_1", res_sample.data)
        self.assertIn(b"parent_email", res_sample.data)

        # 4. Download Student Report
        res_rep = self.client.get("/student/ENG0001/download-report")
        self.assertEqual(res_rep.status_code, 200)
        self.assertIn(b"ENGINEERING STUDENT PERFORMANCE & AI PREDICTION REPORT", res_rep.data)
        self.assertIn(b"ENG0001", res_rep.data)

        # 5. Send Parent Email
        res_email = self.client.post("/student/ENG0001/send-parent-email", data={
            "parent_email": "parent.test@college.edu"
        }, follow_redirects=True)
        self.assertEqual(res_email.status_code, 200)
        self.assertIn(b"successfully sent to parent", res_email.data)

    def test_prediction_without_study_hours(self):
        self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)

        # Prediction POST without study_hours_per_day AND without midterm_score
        pred_res = self.client.post("/predict", data={
            "student_id": "ENGTEST88",
            "name": "Pooja Narayanan",
            "parent_email": "parent.pooja@college.edu",
            "department": "Computer Science and Engineering",
            "semester": "6",
            "age": "21",
            "gender": "Female",
            "attendance_percentage": "88.0",
            "prev_sem_cgpa": "8.4",
            "internal_exam_1": "82.0",
            "internal_exam_2": "86.0",
            "assignment_average": "85.0",
            "lab_score": "82.0",
            "technical_skill_score": "80.0",
            "coding_skill_score": "85.0",
            "communication_skill_score": "78.0",
            "aptitude_score": "80.0",
            "backlogs": "0",
            "previous_failures": "0",
            "class_participation": "8",
            "extracurricular_score": "75.0",
            "project_score": "84.0"
        }, follow_redirects=True)

        self.assertEqual(pred_res.status_code, 200)
        self.assertIn(b"Pooja Narayanan", pred_res.data)
        self.assertIn(b"ENGTEST88", pred_res.data)
        self.assertIn(b"parent.pooja@college.edu", pred_res.data)
        self.assertIn(b"8.4", pred_res.data)
        self.assertIn(b"All Clear", pred_res.data)

        # Verify in database that midterm_score was auto-computed: (82.0 + 86.0) / 2 = 84.0
        with self.app.app_context():
            st = Student.query.filter_by(student_id="ENGTEST88").first()
            self.assertIsNotNone(st)
            self.assertEqual(st.midterm_score, 84.0)
            self.assertEqual(st.arrears, 0)

    def test_csv_import_flow(self):
        self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)

        csv_content = (
            "student_id,name,parent_email,department,semester,age,gender,attendance_percentage,prev_sem_cgpa,internal_exam_1,internal_exam_2\n"
            "ENGCSV01,Kavya Murthy,parent.kavya@college.edu,Computer Science and Engineering,5,20,Female,89.5,8.7,85.0,88.0\n"
            "ENGCSV02,Vikram Das,parent.vikram@college.edu,Mechanical Engineering,6,21,Male,61.0,5.9,48.0,52.0\n"
        )
        data = {
            "csv_file": (io.BytesIO(csv_content.encode("utf-8")), "students_batch.csv")
        }

        res = self.client.post("/import-csv", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"CSV Ingestion Complete", res.data)

        # Verify imported student exists and has prediction
        with self.app.app_context():
            st = Student.query.filter_by(student_id="ENGCSV01").first()
            self.assertIsNotNone(st)
            self.assertEqual(st.name, "Kavya Murthy")
            self.assertIsNotNone(st.latest_prediction)

    def test_edit_student_flow(self):
        self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)

        # GET edit page
        get_res = self.client.get("/student/ENG0001/edit")
        self.assertEqual(get_res.status_code, 200)
        self.assertIn(b"Edit Student Record", get_res.data)
        self.assertIn(b"ENG0001", get_res.data)

        # POST edit update: update marks, semester, and arrears
        post_res = self.client.post("/student/ENG0001/edit", data={
            "name": "Aditya V. Sharma",
            "parent_email": "parent.aditya.updated@college.edu",
            "department": "Computer Science and Engineering",
            "semester": "7",
            "age": "22",
            "gender": "Male",
            "internal_exam_1": "92.0",
            "internal_exam_2": "94.0",
            "prev_sem_cgpa": "9.1",
            "attendance_percentage": "92.0",
            "assignment_average": "90.0",
            "lab_score": "88.0",
            "project_score": "91.0",
            "study_hours_per_day": "5.5",
            "class_participation": "9",
            "extracurricular_score": "80.0",
            "backlogs": "0",
            "previous_failures": "0",
            "technical_skill_score": "88.0",
            "coding_skill_score": "90.0",
            "communication_skill_score": "85.0",
            "aptitude_score": "89.0"
        }, follow_redirects=True)

        self.assertEqual(post_res.status_code, 200)
        self.assertIn(b"successfully updated", post_res.data)

        with self.app.app_context():
            st = Student.query.filter_by(student_id="ENG0001").first()
            self.assertIsNotNone(st)
            self.assertEqual(st.name, "Aditya V. Sharma")
            self.assertEqual(st.semester, 7)
            self.assertEqual(st.internal_exam_1, 92.0)
            self.assertEqual(st.internal_exam_2, 94.0)
            self.assertEqual(st.midterm_score, 93.0)  # (92 + 94) / 2
            self.assertEqual(st.parent_email, "parent.aditya.updated@college.edu")
            self.assertIsNotNone(st.latest_prediction)

    def test_delete_student_flow(self):
        self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)

        # Create temporary student to delete
        with self.app.app_context():
            temp_student = Student(
                student_id="ENGTEMP99",
                name="Temporary Test Student",
                parent_email="parent.temp@college.edu",
                department="Mechanical Engineering",
                semester=4,
                age=20,
                gender="Male",
                attendance_percentage=75.0,
                previous_semester_percentage=72.0,
                internal_exam_1=70.0,
                internal_exam_2=72.0,
                assignment_average=70.0,
                lab_score=70.0,
                midterm_score=71.0,
                project_score=70.0,
                technical_skill_score=68.0,
                coding_skill_score=65.0,
                communication_skill_score=70.0,
                aptitude_score=68.0
            )
            db.session.add(temp_student)
            
            # Create user login for this student
            temp_user = User(
                username="ENGTEMP99",
                role="student",
                student_id="ENGTEMP99"
            )
            temp_user.set_password("student123")
            db.session.add(temp_user)
            db.session.commit()

        # Delete student via POST
        del_res = self.client.post("/student/ENGTEMP99/delete", follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIn(b"has been permanently removed", del_res.data)

        # Verify completely deleted from database
        with self.app.app_context():
            self.assertIsNone(Student.query.filter_by(student_id="ENGTEMP99").first())
            self.assertIsNone(User.query.filter_by(student_id="ENGTEMP99").first())

if __name__ == "__main__":
    unittest.main()

