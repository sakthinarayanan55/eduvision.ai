"""
Vercel Serverless Function Entrypoint.
File: api/index.py
"""

import os
import sys

# Ensure project root directory is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from werkzeug.middleware.proxy_fix import ProxyFix
from app import app
from database.database import init_db

# Trust reverse proxy headers (X-Forwarded-Proto, X-Forwarded-For, etc.) on Vercel
# This prevents HTTPS-to-HTTP redirect loops (ERR_TOO_MANY_REDIRECTS)
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_prefix=1
)

# Ensure database tables and initial dataset exist
with app.app_context():
    try:
        from database.models import User, Student, db
        db.create_all()
        if User.query.count() == 0 or Student.query.count() == 0:
            init_db(app)
    except Exception as e:
        try:
            init_db(app)
        except Exception as e2:
            print(f"Warning: Database initialization error: {e2}")

if __name__ == "__main__":
    app.run()
