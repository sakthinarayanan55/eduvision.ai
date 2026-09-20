"""
Unit tests for Flask Application Web Routes & API Endpoints.
File: tests/test_routes.py
"""

import unittest
import os
import sys
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from database.models import db, User, Student

class TestAppRoutes(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_login_page_renders(self):
        """GET /login should return status code 200."""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"EduVision AI", response.data)

    def test_unauthenticated_redirect(self):
        """Accessing protected routes without session must redirect to /login."""
        for path in ["/dashboard", "/students", "/at-risk", "/interventions", "/model-performance"]:
            response = self.client.get(path, follow_redirects=False)
            self.assertEqual(response.status_code, 302, f"Failed for {path}")
            self.assertIn("/login", response.headers["Location"])

    def test_successful_login(self):
        """POST /login with valid admin credentials should set session and redirect to /dashboard."""
        response = self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Executive Dashboard", response.data)

    def test_api_predict_endpoint(self):
        """POST /api/predict must return JSON prediction with status 200."""
        payload = {
            "student_id": "ENG_API_01",
            "department": "Computer Science and Engineering",
            "semester": 5,
            "age": 20,
            "gender": "Male",
            "attendance_percentage": 90.0,
            "study_hours_per_day": 4.5,
            "previous_semester_percentage": 82.0,
            "internal_exam_1": 78.0,
            "internal_exam_2": 82.0,
            "assignment_average": 85.0,
            "lab_score": 88.0,
            "technical_skill_score": 82.0,
            "coding_skill_score": 80.0,
            "communication_skill_score": 75.0,
            "aptitude_score": 80.0,
            "backlogs": 0,
            "previous_failures": 0,
            "class_participation": 8,
            "extracurricular_score": 70.0,
            "project_score": 84.0,
            "midterm_score": 80.0
        }
        response = self.client.post("/api/predict", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn(data["data"]["predicted_category"], ["High", "Average", "Low"])
        self.assertIn("confidence", data["data"])

    def test_invalid_login(self):
        """POST /login with wrong credentials must show error."""
        response = self.client.post("/login", data={
            "username": "admin",
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid username or password", response.data)

if __name__ == "__main__":
    unittest.main()
