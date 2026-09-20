"""
Application Configuration.
File: config.py
"""

import os
import shutil
import tempfile

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_database_uri():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Normalize legacy Heroku/Supabase postgres:// scheme to postgresql:// for SQLAlchemy 2.0+
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    
    if os.environ.get("VERCEL"):
        # Serverless read-only filesystem handling: use temporary writable directory (/tmp)
        tmp_dir = "/tmp" if os.name != "nt" else tempfile.gettempdir()
        tmp_db = os.path.join(tmp_dir, "student_performance.db")
        bundled_db = os.path.join(BASE_DIR, "student_performance.db")
        
        if not os.path.exists(tmp_db) and os.path.exists(bundled_db):
            try:
                shutil.copy2(bundled_db, tmp_db)
            except Exception as e:
                print(f"Warning: could not copy bundled database to {tmp_db}: {e}")
        return f"sqlite:///{tmp_db}"
        
    return f"sqlite:///{os.path.join(BASE_DIR, 'student_performance.db')}"

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-eng-ai-student-secret-key-2026")
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Model Artifacts
    MODEL_PATH = os.path.join(BASE_DIR, "models", "student_performance_model.pkl")
    METRICS_PATH = os.path.join(BASE_DIR, "models", "model_metrics.json")
    DATASET_PATH = os.path.join(BASE_DIR, "data", "engineering_student_performance.csv")
