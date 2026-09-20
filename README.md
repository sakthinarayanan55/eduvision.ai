# EduVision-AI

### AI-Based Engineering Student Performance Prediction and Early Intervention System

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Backend-Flask%203.1-black.svg)](https://palletsprojects.com/p/flask/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-orange.svg)](https://scikit-learn.org/)
[![Plotly](https://img.shields.io/badge/Charts-Plotly.js-indigo.svg)](https://plotly.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end, production-style AI/ML web application designed specifically for engineering colleges and universities. The system analyzes multi-dimensional engineering student academic and behavioral indicators, predicts end-semester performance categories using trained machine learning pipelines, computes transparent multi-factor risk tiers, highlights key model indicators without unfounded causal assertions, and generates actionable, personalized early interventions for academic mentors.

---

## 🌟 Key System Features

- **Multi-Role Authentication & Access Control**:
  - **Admin**: Cohort analytics, system-wide diagnostics, student management, and model benchmark oversight.
  - **Faculty / Mentor**: Assigned student 360° analytics, real-time ML inference, risk diagnostics, early intervention action logging, and status tracking.
  - **Student**: Personalized academic standing, model predicted outcome, skill radar visualization, and remediation action plans.
- **Leakage-Free Machine Learning Architecture**:
  - Predicts multi-class performance outcome: **`High`**, **`Average`**, **`Low`**.
  - Strict prevention of target leakage: `final_exam_score` is strictly excluded from training and inference feature matrices.
  - Trained across 5 competing algorithms: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, and SVM.
  - Automatically selects optimal model by test weighted F1-score with persistence in `models/student_performance_model.pkl`.
- **Transparent Multi-Factor Risk Engine (`services/risk_engine.py`)**:
  - Classifies students into **`LOW RISK`**, **`MEDIUM RISK`**, and **`HIGH RISK`** using clear, documented, regulatory-compliant criteria (including the university 75% attendance threshold, active backlogs, internal assessment averages, and study hours).
- **Rule-Based Early Intervention Engine (`services/intervention_engine.py`)**:
  - Automatically prescribes prioritized, actionable interventions triggered strictly by actual student deficits (e.g., peer mentoring, programming labs, time-blocked study schedules, re-examinations).
- **Interactive Executive Dashboard**:
  - 6 executive KPI cards and 6 interactive Plotly.js charts:
    1. Performance Category Share (Donut)
    2. Risk Tier Distribution (Bar)
    3. Department Outcomes Comparison (Grouped Bar)
    4. Attendance vs. Outcome (Box Plot)
    5. Daily Study Hours Histogram
    6. Uncleared Backlogs Distribution
- **Model Performance & Explainability Page**:
  - Dynamic display of real dataset statistics (1,250 records, 30 features after encoding), model benchmark comparison table, confusion matrix heatmap, and tree-based feature importance weights.
- **RESTful API Endpoint**:
  - `POST /api/predict` for programmatic inference and external LMS/ERP integration.

---

## 🏛️ System Architecture

```
                                  +---------------------------------------+
                                  |   data/engineering_student_perf.csv   |
                                  +---------------------------------------+
                                                      |
                                                      v
                                        +---------------------------+
                                        |   ml/train_model.py       |
                                        |  - ColumnTransformer      |
                                        |  - Stratified 80/20 Split |
                                        |  - 5-Model Benchmark      |
                                        +---------------------------+
                                                      |
                                                      v
                                        +---------------------------+
                                        | models/                   |
                                        |  - student_model.pkl      |
                                        |  - model_metrics.json     |
                                        +---------------------------+
                                                      |
                                                      v
+------------------------+             +-----------------------------+             +------------------------+
| Client / Web Browser   | <=========> | Flask Web App (app.py)      | <=========> | SQLite Database        |
| - Jinja2 Templates     |             |  - services/risk_engine.py  |             |  - User Credentials    |
| - Bootstrap 5 & Custom |             |  - services/intervention.py |             |  - Student Records     |
| - Plotly.js Charts     |             |  - services/analytics.py    |             |  - Predictions History |
+------------------------+             +-----------------------------+             |  - Intervention Logs   |
                                                                                   +------------------------+
```

---

## 💻 Tech Stack

- **Backend**: Python 3.11+, Flask 3.1, Werkzeug (Security & Password Hashing)
- **Database & ORM**: SQLite 3, SQLAlchemy 2.0, Flask-SQLAlchemy 3.1
- **Machine Learning**: Scikit-Learn 1.6+, Pandas 2.2+, NumPy 1.26+, Joblib 1.4+
- **Data Visualization**: Plotly 6.0+, Plotly.js 2.29
- **Frontend**: HTML5, Vanilla CSS3 (Custom Academic Theme), Bootstrap 5.3, Bootstrap Icons 1.11

---

## 📋 Default Demonstration Credentials

The application is pre-seeded with three logical user accounts for testing and demonstration:

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Full administrative access, cohort analytics, model diagnostics |
| **Faculty / Mentor** | `faculty` | `faculty123` | Student analytics, prediction form, intervention tracking |
| **Student** | `student` | `student123` | Student self-service portal (linked to `ENG0001`) |

*(Note: 1-click login buttons are also provided on the login page for convenience during project evaluations).*

---

## 🚀 Windows Installation & Running Guide

### 1. Clone or Open the Workspace Directory
```powershell
cd c:\Users\ELCOT\OneDrive\Desktop\project
```

### 2. Set Up Virtual Environment (Recommended)
```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 4. (Optional) Re-Train the Machine Learning Pipeline
*(The repository already includes the pre-trained pipeline and metrics, but you can retrain anytime):*
```powershell
python ml/train_model.py
```
*Output: Evaluates all 5 classifiers, selects the best model, and exports `models/student_performance_model.pkl` and `models/model_metrics.json`.*

### 5. Start the Flask Application
```powershell
python app.py
```

Open your browser and navigate to:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Automated Testing

Execute the comprehensive unit test suite covering ML prediction, preprocessing, missing feature imputation, risk classification rules, intervention rules, and Flask authentication routes:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

All 19 test cases will run and report status.

---

## 📡 REST API Endpoint Documentation

### Endpoint: `POST /api/predict`
Executes real-time machine learning inference, risk calculation, indicator extraction, and early intervention generation.

#### Sample Request Payload:
```json
{
  "student_id": "ENG9999",
  "department": "Computer Science and Engineering",
  "semester": 5,
  "age": 20,
  "gender": "Male",
  "attendance_percentage": 64.0,
  "study_hours_per_day": 1.5,
  "previous_semester_percentage": 54.0,
  "internal_exam_1": 45.0,
  "internal_exam_2": 48.0,
  "assignment_average": 55.0,
  "lab_score": 58.0,
  "technical_skill_score": 46.0,
  "coding_skill_score": 42.0,
  "communication_skill_score": 58.0,
  "aptitude_score": 50.0,
  "backlogs": 2,
  "previous_failures": 2,
  "class_participation": 3,
  "extracurricular_score": 40.0,
  "project_score": 52.0,
  "midterm_score": 46.0
}
```

#### Sample JSON Response:
```json
{
  "status": "success",
  "data": {
    "student_id": "ENG9999",
    "predicted_category": "Low",
    "confidence": 90.7,
    "model_used": "Random Forest",
    "risk_level": "HIGH RISK",
    "risk_score": 75,
    "probabilities": {
      "High": 0.015,
      "Average": 0.078,
      "Low": 0.907
    },
    "indicators": [
      {
        "indicator": "Active Backlogs",
        "value": "2 subjects",
        "status": "danger",
        "note": "Substantial weight in risk and performance assessment"
      },
      {
        "indicator": "Class Attendance",
        "value": "64.0%",
        "status": "danger",
        "note": "Below minimum regulatory 75% attendance threshold"
      }
    ],
    "interventions": [
      {
        "type": "Attendance Alert",
        "priority": "High",
        "trigger": "Current Attendance: 64.0% (< 75% regulatory requirement)",
        "recommendation": "Monitor attendance and encourage regular class participation.",
        "action_plan": "Notify mentor; issue official attendance deficit warning; schedule weekly attendance check-in."
      }
    ]
  }
}
```

---

## 🔒 Data Privacy & Ethics Note

Student records constitute sensitive educational data. To safeguard student privacy:
- The dataset utilizes **100% synthetic, anonymized records** (`ENG0001` through `ENG1250`).
- No personally identifiable information (PII) such as real student names, contact numbers, residential addresses, or email IDs are stored or collected.
- Indicators and model explanations are deliberately worded using non-causal language ("Important model indicators" rather than causal claims) to support formative mentoring rather than punitive labeling.

---

## 🔮 Future Enhancements

1. **Explainable AI (SHAP & LIME)**: Adding live force plots and waterfall graphs for individual local prediction explainability.
2. **Automated Notification System**: Email/SMS integration to alert parents and mentors when a student transitions into High Risk.
3. **LMS / Biometric Integration**: Direct API connectors with Moodle, Canvas, and campus RFID attendance turnstiles.
4. **Time-Series Performance Forecasting**: LSTM or Transformer-based sequential trajectory modeling over 8 continuous semesters.
5. **Mobile Application**: Flutter/React Native mobile companion app for students and faculty mentors.
