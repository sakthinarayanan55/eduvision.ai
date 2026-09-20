"""
Data preprocessing and pipeline definition for Engineering Student Performance Prediction.
File: ml/preprocess.py
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# Identifier and target columns (strictly omitted from model training)
EXCLUDE_COLUMNS = ["student_id", "final_exam_score", "performance_category"]

CATEGORICAL_FEATURES = ["department", "gender"]

NUMERICAL_FEATURES = [
    "semester",
    "age",
    "attendance_percentage",
    "study_hours_per_day",
    "previous_semester_percentage",
    "internal_exam_1",
    "internal_exam_2",
    "assignment_average",
    "lab_score",
    "technical_skill_score",
    "coding_skill_score",
    "communication_skill_score",
    "aptitude_score",
    "backlogs",
    "previous_failures",
    "class_participation",
    "extracurricular_score",
    "project_score",
    "midterm_score"
]

TARGET_COLUMN = "performance_category"
TARGET_CLASSES = ["High", "Average", "Low"]

def get_preprocessor():
    """
    Constructs a robust ColumnTransformer that scales numerical variables
    and one-hot encodes categorical variables, with imputation for missing values.
    """
    num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])

    cat_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipeline, NUMERICAL_FEATURES),
            ("cat", cat_pipeline, CATEGORICAL_FEATURES)
        ],
        remainder="drop"
    )
    return preprocessor

def clean_and_split_data(df):
    """
    Validates input dataframe, strips leakage columns,
    and returns feature matrix X and target series y.
    """
    df_clean = df.copy()
    
    # Validation checks
    assert TARGET_COLUMN in df_clean.columns, f"Target column '{TARGET_COLUMN}' missing from dataframe."
    
    y = df_clean[TARGET_COLUMN]
    
    # Feature matrix: ensure leakage columns like final_exam_score are strictly excluded
    feature_cols = [col for col in NUMERICAL_FEATURES + CATEGORICAL_FEATURES if col in df_clean.columns]
    X = df_clean[feature_cols]
    
    return X, y
