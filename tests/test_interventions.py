"""
Unit tests for Early Intervention Engine.
File: tests/test_interventions.py
"""

import unittest
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.intervention_engine import generate_interventions

class TestInterventionEngine(unittest.TestCase):
    def test_low_attendance_rule(self):
        """Attendance < 75% must trigger attendance alert."""
        student = {"attendance_percentage": 68.0}
        recs = generate_interventions(student)
        rec_texts = [r["recommendation"] for r in recs]
        self.assertTrue(any("attendance" in t.lower() for t in rec_texts))

    def test_low_study_hours_rule(self):
        """Study hours < 2 must trigger daily study schedule recommendation."""
        student = {"study_hours_per_day": 1.2, "attendance_percentage": 85.0}
        recs = generate_interventions(student)
        rec_texts = [r["recommendation"] for r in recs]
        self.assertTrue(any("study schedule" in t.lower() for t in rec_texts))

    def test_active_backlogs_rule(self):
        """Backlogs > 0 must trigger backlog-clearing study plan."""
        student = {"backlogs": 2, "attendance_percentage": 85.0}
        recs = generate_interventions(student)
        rec_texts = [r["recommendation"] for r in recs]
        self.assertTrue(any("backlog" in t.lower() for t in rec_texts))

    def test_coding_skill_rule_for_cs_branches(self):
        """Coding skill < 50 for CSE/IT/AI branches must trigger programming practice."""
        student = {
            "department": "Computer Science and Engineering",
            "coding_skill_score": 42.0,
            "attendance_percentage": 85.0
        }
        recs = generate_interventions(student)
        rec_texts = [r["recommendation"] for r in recs]
        self.assertTrue(any("programming practice" in t.lower() for t in rec_texts))

    def test_high_performer_enrichment(self):
        """High performer with no deficits should receive enrichment advice."""
        student = {
            "attendance_percentage": 92.0,
            "study_hours_per_day": 4.5,
            "backlogs": 0,
            "assignment_average": 85.0,
            "technical_skill_score": 85.0,
            "coding_skill_score": 80.0,
            "communication_skill_score": 80.0,
            "internal_exam_1": 85.0,
            "internal_exam_2": 85.0
        }
        recs = generate_interventions(student, predicted_category="High")
        self.assertGreater(len(recs), 0)
        self.assertEqual(recs[0]["type"], "Academic Enrichment")

if __name__ == "__main__":
    unittest.main()
