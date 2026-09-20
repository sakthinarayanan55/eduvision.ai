# Vercel Deployment Guide - EduVision-AI

This guide provides instructions for deploying the **EduVision-AI** Flask web application to **Vercel**.

---

## Architecture Overview

On Vercel, this application runs using Vercel's native **Python Serverless Functions** runtime:
- **Routing**: `vercel.json` rewrites all incoming HTTP requests to `/api/index.py`.
- **Serverless Entrypoint**: [`api/index.py`](api/index.py) exports the Flask `app` WSGI instance.
- **Assets & Models**: `templates/`, `static/`, `models/`, and `data/` are bundled directly into the function bundle via `includeFiles` in `vercel.json`.
- **Database Modes**:
  - **Zero-Setup (Default)**: If `DATABASE_URL` is omitted, the bundled `student_performance.db` is copied to `/tmp/student_performance.db` (the only writable directory in AWS Lambda/Vercel). All pre-seeded accounts, 1000 students, and ML models work immediately.
  - **Production Persistent DB (Recommended)**: Set the `DATABASE_URL` environment variable in Vercel to point to a free PostgreSQL database (e.g., [Neon](https://neon.tech), [Supabase](https://supabase.com), or Vercel Postgres).

---

## Method 1: Deploy via GitHub & Vercel Dashboard (Recommended)

Because your repository is already set up on GitHub (`sakthinarayanan55/EduVision-AI`), this is the easiest and most automated deployment method:

### Step 1: Commit and Push the Vercel Files
In your terminal, run:
```bash
git add config.py api/index.py vercel.json .vercelignore .python-version VERCEL_DEPLOYMENT.md
git commit -m "Configure Vercel serverless deployment"
git push origin main
```

### Step 2: Import into Vercel
1. Go to [https://vercel.com](https://vercel.com) and log in with your GitHub account.
2. Click **"Add New..."** > **"Project"**.
3. Locate **`EduVision-AI`** from your repository list and click **"Import"**.
4. In the project configuration:
   - **Framework Preset**: Leave as *Other* (Vercel automatically detects Python & `vercel.json`).
   - **Root Directory**: `./` (default).
5. (Optional) Under **Environment Variables**, add:
   - `SECRET_KEY`: A random secure string (e.g., `my-super-secret-key-eduvision-2026`).
   - `DATABASE_URL` *(Optional)*: If you want persistent PostgreSQL storage instead of the demo SQLite database.
6. Click **"Deploy"**.

Vercel will install the dependencies from `requirements.txt`, bundle the application, and assign a live production URL (e.g. `https://eduvision-ai.vercel.app`).

---

## Method 2: Deploy via Vercel CLI

If you prefer deploying directly from your local terminal:

1. **Install the Vercel CLI** (if not already installed):
   ```bash
   npm install -g vercel
   ```

2. **Log in to your Vercel account**:
   ```bash
   vercel login
   ```

3. **Deploy to Preview**:
   ```bash
   vercel
   ```
   Follow the interactive prompts (select defaults by pressing Enter).

4. **Deploy to Production**:
   ```bash
   vercel --prod
   ```

---

## Default Login Credentials

Once your app is deployed, you can log in using any of the pre-seeded accounts:

| Role | Username | Password |
| :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` |
| **Faculty** | `faculty` | `faculty123` |
| **Student** | `student` *(or `ENG0001`)* | `student123` |

---

## Environment Variables Reference

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | Recommended | Flask session secret key | `super-secret-random-key` |
| `DATABASE_URL` | Optional | Connection string for external PostgreSQL database | `postgresql://user:pass@ep-host.neon.tech/neondb?sslmode=require` |
| `VERCEL` | Automatic | Automatically set to `1` by Vercel | `1` |
