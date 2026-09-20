"""
Unit tests for Risk Engine.
File: tests/test_risk.py
"""

import unittest
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.risk_engine import calculate_student_risk

class TestRiskEngine(unittest.TestCase):
    def test_low_risk_profile(self):
        """Top-performing student with high attendance and zero backlogs should be LOW RISK."""
        high_student = {
            "attendance_percentage": 92.0,
            "backlogs": 0,
            "previous_semester_percentage": 88.0,
            "internal_exam_1": 85.0,
            "internal_exam_2": 88.0,
            "study_hours_per_day": 5.0,
            "coding_skill_score": 80.0,
            "technical_skill_score": 85.0
        }
        res = calculate_student_risk(high_student, predicted_category="High")
        self.assertEqual(res["risk_level"], "LOW RISK")
        self.assertLess(res["risk_score"], 20)

    def test_high_risk_profile(self):
        """Student with critical attendance deficit and multiple backlogs should be HIGH RISK."""
        risk_student = {
            "attendance_percentage": 58.0,
            "backlogs": 3,
            "previous_semester_percentage": 48.0,
            "internal_exam_1": 38.0,
            "internal_exam_2": 42.0,
            "study_hours_per_day": 1.0,
            "coding_skill_score": 35.0,
            "technical_skill_score": 40.0
        }
        res = calculate_student_risk(risk_student, predicted_category="Low")
        self.assertEqual(res["risk_level"], "HIGH RISK")
        self.assertGreaterEqual(res["risk_score"], 45)
        self.assertGreater(len(res["risk_factors"]), 1)

    def test_medium_risk_profile(self):
        """Borderline student with 1 backlog or sub-75% attendance should trigger MEDIUM RISK."""
        med_student = {
            "attendance_percentage": 72.0,
            "backlogs": 1,
            "previous_semester_percentage": 64.0,
            "internal_exam_1": 60.0,
            "internal_exam_2": 62.0,
            "study_hours_per_day": 2.5,
            "coding_skill_score": 58.0,
            "technical_skill_score": 60.0
        }
        res = calculate_student_risk(med_student, predicted_category="Average")
        self.assertEqual(res["risk_level"], "MEDIUM RISK")

    def test_risk_score_bounds(self):
        """Risk score must always stay between 0 and 100."""
        extreme_student = {
            "attendance_percentage": 20.0,
            "backlogs": 6,
            "previous_semester_percentage": 30.0,
            "internal_exam_1": 20.0,
            "internal_exam_2": 25.0,
            "study_hours_per_day": 0.2,
            "coding_skill_score": 15.0,
            "technical_skill_score": 20.0
        }
        res = calculate_student_risk(extreme_student, predicted_category="Low")
        self.assertLessEqual(res["risk_score"], 100)
        self.assertGreaterEqual(res["risk_score"], 0)

if __name__ == "__main__":
    unittest.main()
