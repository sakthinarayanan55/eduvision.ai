"""
Unit tests for Machine Learning Prediction and Preprocessing.
File: tests/test_prediction.py
"""

import unittest
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.predict import predict_student_performance, get_model
from ml.preprocess import TARGET_CLASSES

class TestModelPrediction(unittest.TestCase):
    def setUp(self):
        self.valid_student = {
            "student_id": "ENG_TEST_01",
            "department": "Computer Science and Engineering",
            "semester": 5,
            "age": 20,
            "gender": "Male",
            "attendance_percentage": 85.0,
            "study_hours_per_day": 4.0,
            "previous_semester_percentage": 75.0,
            "internal_exam_1": 70.0,
            "internal_exam_2": 72.0,
            "assignment_average": 78.0,
            "lab_score": 80.0,
            "technical_skill_score": 75.0,
            "coding_skill_score": 70.0,
            "communication_skill_score": 68.0,
            "aptitude_score": 72.0,
            "backlogs": 0,
            "previous_failures": 0,
            "class_participation": 7,
            "extracurricular_score": 60.0,
            "project_score": 76.0,
            "midterm_score": 71.0
        }

    def test_model_loading(self):
        """Ensure trained model artifact loads correctly."""
        artifact = get_model()
        self.assertIn("pipeline", artifact)
        self.assertIn("model_name", artifact)
        self.assertEqual(artifact["classes"], TARGET_CLASSES)

    def test_valid_student_prediction(self):
        """Ensure valid student input returns expected prediction structure."""
        result = predict_student_performance(self.valid_student)
        self.assertIn(result["predicted_category"], TARGET_CLASSES)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 100.0)
        self.assertIn(result["risk_level"], ["LOW RISK", "MEDIUM RISK", "HIGH RISK"])
        self.assertIsInstance(result["probabilities"], dict)
        self.assertAlmostEqual(sum(result["probabilities"].values()), 1.0, places=2)

    def test_missing_feature_handling(self):
        """Ensure pipeline handles missing optional fields via imputer."""
        incomplete_student = self.valid_student.copy()
        del incomplete_student["study_hours_per_day"]
        del incomplete_student["lab_score"]
        result = predict_student_performance(incomplete_student)
        self.assertIn(result["predicted_category"], TARGET_CLASSES)

    def test_indicators_extraction(self):
        """Ensure indicators are identified with non-causal phrasing."""
        result = predict_student_performance(self.valid_student)
        self.assertIsInstance(result["indicators"], list)
        self.assertGreater(len(result["indicators"]), 0)
        for ind in result["indicators"]:
            self.assertIn("indicator", ind)
            self.assertIn("value", ind)
            self.assertIn("status", ind)

    def test_invalid_attendance_and_edge_cases(self):
        """Ensure system handles sub-zero or extreme attendance and generates high risk alert."""
        low_att_student = self.valid_student.copy()
        low_att_student["attendance_percentage"] = 35.0
        low_att_student["backlogs"] = 3
        result = predict_student_performance(low_att_student)
        self.assertEqual(result["risk_level"], "HIGH RISK")
        # Ensure attendance alert is in interventions
        recs = [i["recommendation"] for i in result["interventions"]]
        self.assertTrue(any("attendance" in r.lower() for r in recs))

if __name__ == "__main__":
    unittest.main()
