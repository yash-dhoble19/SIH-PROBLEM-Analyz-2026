# SIH 2026 Intelligence Platform — Free Production Deployment Guide

This guide details how to deploy the **SIH 2026 Project Intelligence Platform** for **FREE** on **Vercel** or **Render**, including how to track visitor analytics, collect project ratings, and configure environment variables.

---

## 🎯 The "Proper Prompt" for Deployment

If you are using Cursor, Claude, GitHub Copilot, or any AI assistant to deploy or manage your project, copy and paste this exact prompt:

```markdown
Deploy the SIH 2026 Project Intelligence Platform (FastAPI + Neon PostgreSQL + pgvector + Vanilla JS Glassmorphic UI) to Vercel/Render.

Key Requirements:
1. Server Entrypoint: api/index.py (for Vercel serverless) and app:app (for Render/Uvicorn).
2. Database: Connect to Neon PostgreSQL using the pooled connection string in DATABASE_URL. Ensure pgvector extension and schema tables (problem_statements, repositories, repository_analyses, problem_matches, visitor_logs, project_ratings) are initialized.
3. Real-Time Tracking: Ensure /api/analytics/visit logs unique sessions and /api/analytics/stats serves live user count.
4. Ratings Panel: Ensure /api/ratings and /api/ratings/stats handle 1-5 star user reviews and display them in the glassmorphic modal.
5. Static Assets: Serve static/ directly with cache headers.
6. Environment Variables:
   - DATABASE_URL (Neon PostgreSQL pooled connection)
   - AI_PROVIDER=auto
   - EMBEDDING_PROVIDER=auto
   - GROQ_API_KEY (optional, high-speed LLM inferences)
   - GITHUB_TOKEN (optional, increases GitHub API rate limits to 5,000 req/hr)
```

---

## 🚀 Option 1: Deploy on Vercel (100% Free & Fast)

Vercel is free, provides instant global CDN caching, and automatic SSL.

### Step 1: Push Code to GitHub
Make sure your latest code is pushed to your GitHub repository:
```bash
git add .
git commit -m "feat: add vercel serverless support, visitor analytics counter, and rating panel"
git push origin main
```

### Step 2: Import into Vercel
1. Go to **[vercel.com](https://vercel.com)** and log in with your GitHub account.
2. Click **"Add New..."** ➔ **"Project"**.
3. Select your repository (`SIH-PROBLEM-Analyz-2026` or `sih-platform`).
4. **Framework Preset**: Select `Other` (or leave default, Vercel detects `vercel.json`).
5. **Root Directory**: `./` (default).

### Step 3: Add Environment Variables in Vercel
In the Vercel project settings, open **"Environment Variables"** and add:

| Key | Example Value | Required? |
|---|---|---|
| `DATABASE_URL` | `postgresql://neondb_owner:npg_...aws.neon.tech/neondb?sslmode=require` | **YES** |
| `AI_PROVIDER` | `auto` | Optional |
| `EMBEDDING_PROVIDER` | `auto` | Optional |
| `GROQ_API_KEY` | `gsk_...` (from console.groq.com) | Recommended |
| `GITHUB_TOKEN` | `ghp_...` | Optional |

### Step 4: Click "Deploy"
Vercel will build your project using `@vercel/python` and provide a live public URL (e.g. `https://sih-intelligence.vercel.app`).

---

## 🌐 Option 2: Deploy on Render.com (100% Free - Full Long-Running Python Support)

If you plan to run heavy multi-agent repository scanning jobs (which take > 15 seconds), Render Web Services is ideal:

1. Go to **[render.com](https://render.com)** and sign up / log in.
2. Click **"New +"** ➔ **"Web Service"**.
3. Connect your GitHub repository.
4. Set the following build settings:
   - **Name**: `sih-2026-platform`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
5. Under **"Environment Variables"**, add:
   - `DATABASE_URL`: *(Your Neon PostgreSQL connection string)*
   - `AI_PROVIDER`: `auto`
   - `GROQ_API_KEY`: *(Your Groq API key)*
6. Click **"Create Web Service"**.

---

## 📊 Testing Your Deployed Platform

Once deployed:
1. **Open the Live URL**:
   - Verify the landing page loads with the live visitor counter: `👥 140+ Users | ⭐ 4.9 (18)`
2. **Submit a Rating**:
   - Click the **"⭐ Rate Us"** button or the floating pill in the bottom-right.
   - Select stars (1-5), pick a tag, write feedback, and click **Submit**.
   - Verify the rating updates in real-time in the community stream.
3. **Search & Explore**:
   - Search for keywords (e.g. `disaster`, `AI`, `cybersecurity`).
   - Click a problem card ➔ open the detail modal ➔ click **"⭐ Rate This Problem"**.
4. **Analyze a Repository**:
   - Paste any GitHub URL (e.g., `https://github.com/facebook/react` or your own repo) to verify AI matching.
