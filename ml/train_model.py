"""
Model training and multi-model evaluation pipeline.
File: ml/train_model.py

Trains:
1. Logistic Regression
2. Decision Tree
3. Random Forest
4. Gradient Boosting
5. Support Vector Machine (SVM)

Selects the optimal model based on Test Weighted F1-score (balancing multi-class precision & recall).
Exports:
- models/student_performance_model.pkl
- models/model_metrics.json
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC

from ml.preprocess import (
    get_preprocessor,
    clean_and_split_data,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    TARGET_CLASSES,
    TARGET_COLUMN
)
from ml.evaluate_model import evaluate_predictions

def train_and_evaluate_models(data_path="data/engineering_student_performance.csv", models_dir="models"):
    os.makedirs(models_dir, exist_ok=True)
    
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}. Please run data/generate_dataset.py first.")
        
    print(f"Loading dataset from: {data_path}")
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} records with {df.shape[1]} columns.")
    
    # Missing value & duplicate detection
    missing_count = df.isnull().sum().sum()
    duplicate_count = df.duplicated().sum()
    print(f"Missing values: {missing_count}, Duplicate rows: {duplicate_count}")
    
    # Class distribution
    class_counts = df[TARGET_COLUMN].value_counts().to_dict()
    print(f"Target distribution: {class_counts}")
    
    X, y = clean_and_split_data(df)
    
    # Stratified Train-Test Split (80/20 split, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )
    print(f"Training records: {len(X_train)}, Testing records: {len(X_test)}")
    
    # Candidate classifiers
    candidate_models = {
        "Logistic Regression": LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        ),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=6,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            min_samples_split=4,
            class_weight="balanced",
            random_state=42
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            random_state=42
        ),
        "Support Vector Machine": SVC(
            probability=True,
            kernel="rbf",
            class_weight="balanced",
            random_state=42
        )
    }
    
    evaluation_results = {}
    fitted_pipelines = {}
    
    print("\n--- Training and Evaluating Models ---")
    for name, clf in candidate_models.items():
        preprocessor = get_preprocessor()
        pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", clf)
        ])
        
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        
        metrics = evaluate_predictions(y_test, y_pred, target_names=TARGET_CLASSES)
        evaluation_results[name] = metrics
        fitted_pipelines[name] = pipe
        
        print(f"[{name}] Acc: {metrics['accuracy']:.4f} | Prec: {metrics['precision_weighted']:.4f} | Rec: {metrics['recall_weighted']:.4f} | F1: {metrics['f1_weighted']:.4f}")
        
    # Model Selection Criterion:
    # Selected by highest weighted F1 score on the held-out test set
    best_model_name = max(evaluation_results, key=lambda k: evaluation_results[k]["f1_weighted"])
    best_pipeline = fitted_pipelines[best_model_name]
    best_metrics = evaluation_results[best_model_name]
    
    print(f"\n==================================================")
    print(f"Selected Optimal Model: {best_model_name}")
    print(f"Selection Criterion: Highest Weighted F1-Score ({best_metrics['f1_weighted']:.4f})")
    print(f"==================================================")
    
    # Extract feature names & importances
    preprocessor = best_pipeline.named_steps["preprocessor"]
    clf = best_pipeline.named_steps["classifier"]
    
    # Get feature names after one-hot encoding
    try:
        cat_encoder = preprocessor.named_transformers_["cat"].named_steps["onehot"]
        encoded_cat_features = cat_encoder.get_feature_names_out(CATEGORICAL_FEATURES).tolist()
    except Exception:
        encoded_cat_features = [f"cat_{i}" for i in range(len(CATEGORICAL_FEATURES))]
        
    all_feature_names = NUMERICAL_FEATURES + encoded_cat_features
    
    feature_importances = []
    if hasattr(clf, "feature_importances_"):
        raw_importances = clf.feature_importances_
        for feat, imp in zip(all_feature_names, raw_importances):
            feature_importances.append({"feature": feat, "importance": round(float(imp), 4)})
        feature_importances.sort(key=lambda x: x["importance"], reverse=True)
    elif hasattr(clf, "coef_"):
        # Average absolute coefficients across classes
        mean_coef = np.mean(np.abs(clf.coef_), axis=0)
        for feat, imp in zip(all_feature_names, mean_coef):
            feature_importances.append({"feature": feat, "importance": round(float(imp), 4)})
        feature_importances.sort(key=lambda x: x["importance"], reverse=True)
    else:
        # Permutation or fallback: use Random Forest importances as surrogate feature importance
        rf_clf = fitted_pipelines["Random Forest"].named_steps["classifier"]
        for feat, imp in zip(all_feature_names, rf_clf.feature_importances_):
            feature_importances.append({"feature": feat, "importance": round(float(imp), 4)})
        feature_importances.sort(key=lambda x: x["importance"], reverse=True)
        
    # Prepare comparison table
    comparison_table = []
    for name, res in evaluation_results.items():
        comparison_table.append({
            "model": name,
            "accuracy": res["accuracy"],
            "precision": res["precision_weighted"],
            "recall": res["recall_weighted"],
            "f1_score": res["f1_weighted"],
            "is_selected": (name == best_model_name)
        })
        
    # Compile comprehensive metadata artifact
    metadata = {
        "dataset_size": len(df),
        "train_records": len(X_train),
        "test_records": len(X_test),
        "feature_count": len(all_feature_names),
        "target_classes": TARGET_CLASSES,
        "class_distribution": class_counts,
        "selected_model": best_model_name,
        "selection_criterion": "Highest Test Weighted F1-Score",
        "comparison_table": comparison_table,
        "models_evaluation": evaluation_results,
        "feature_importances": feature_importances[:15],
        "all_feature_names": all_feature_names
    }
    
    # Save best model pipeline
    model_save_path = os.path.join(models_dir, "student_performance_model.pkl")
    joblib.dump({
        "pipeline": best_pipeline,
        "model_name": best_model_name,
        "classes": TARGET_CLASSES,
        "numerical_features": NUMERICAL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES
    }, model_save_path)
    print(f"Saved optimal model pipeline to {model_save_path}")
    
    # Save model metrics json
    metrics_save_path = os.path.join(models_dir, "model_metrics.json")
    with open(metrics_save_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved model evaluation metrics to {metrics_save_path}")
    
    return metadata

if __name__ == "__main__":
    train_and_evaluate_models()
