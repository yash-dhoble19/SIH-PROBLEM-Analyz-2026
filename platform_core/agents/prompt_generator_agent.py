"""
Agent 9: Coding Prompt Generator.
Generates implementation-level prompts tailored for AI coding assistants (Cursor, Claude Code, Antigravity, Gemini).
"""

from typing import Dict, Any, List
from platform_core.agents.base import BaseAgent


class PromptGeneratorAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 9: Coding Prompt Generator", ai_provider)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        analysis_data = context.get("analysis_data", {})
        problem_analysis = context.get("problem_analysis", {})
        plan_data = context.get("plan_data", {})
        repo_info = context.get("repo_info", {})
        
        ps_summary = problem_analysis.get("problem_summary") or "SIH Problem Statement"
        category = problem_analysis.get("category") or "Software"
        theme = problem_analysis.get("theme") or "General"
        
        backend = analysis_data.get("backend_framework") or "FastAPI"
        frontend = analysis_data.get("frontend_framework") or "Web UI"
        detected_langs = analysis_data.get("detected_languages") or ["Python"]
        languages = ", ".join(detected_langs)

        prompts = []

        # 1. Backend & Ingestion Prompt
        prompt_backend = f"""# PROMPT 1: BACKEND API & DATA INGESTION ENGINE
**Target Assistant:** Cursor / Claude Code / Antigravity / Gemini

## PROJECT CONTEXT
You are working on the repository `{repo_info.get('repo_name', 'project')}`, which is being evolved to satisfy the Smart India Hackathon problem statement:
**{ps_summary}** (Theme: {theme}, Track: {category})

## CURRENT REPOSITORY STRUCTURE
- Primary Language: {languages}
- Backend Framework: {backend}
- Existing Capabilities: {', '.join(analysis_data.get('technical_capabilities') or ['REST API Services'])}

## SIH REQUIREMENT & GAPS
The SIH problem requires a real-time data ingestion pipeline and analytical endpoints to support {theme} monitoring.

## TASK
Extend the existing `{backend}` backend to add real-time domain telemetry ingestion, analytics endpoints, and event validation.

## FILES TO MODIFY
- `main.py` / `app.py`: Register the new analytics router and dependency injection.

## FILES TO CREATE
- `routers/analytics_router.py`: Implement endpoints (`GET /api/v1/metrics`, `POST /api/v1/telemetry`, `GET /api/v1/alerts`).
- `services/telemetry_service.py`: Business logic for stream parsing, threshold evaluation, and alert dispatch.

## TECHNICAL REQUIREMENTS
1. Use Pydantic models for strict request/response schema validation.
2. Implement async endpoint handlers with non-blocking I/O.
3. Integrate structured JSON error responses with proper HTTP status codes.

## ACCEPTANCE CRITERIA
- Ingestion endpoint validates and records incoming telemetry.
- Analytics endpoint returns summary metrics and current risk levels.
- All existing endpoints continue to function without regression.

## TESTING REQUIREMENTS
- Write unit tests in `tests/test_analytics.py` verifying status codes (200, 422).

## CRITICAL RULE
**DO NOT BREAK EXISTING FEATURES.** Preserve all existing routes, models, and utility functions."""

        prompts.append({
            "category": "Backend",
            "title": "Backend Telemetry & Analytics Ingestion API",
            "prompt_text": prompt_backend,
            "target_tools": ["Cursor", "Claude Code", "Antigravity", "Gemini"]
        })

        # 2. AI/ML Prediction Model Prompt
        prompt_ml = f"""# PROMPT 2: DOMAIN AI/ML PREDICTION & INFERENCE ENGINE
**Target Assistant:** Cursor / Claude Code / Antigravity / Gemini

## PROJECT CONTEXT
Repository `{repo_info.get('repo_name', 'project')}` targeting SIH Problem: **{ps_summary}**.

## EXISTING IMPLEMENTATION
- ML Capabilities Detected: {', '.join(analysis_data.get('ml_capabilities') or ['Data Processing Engine'])}

## TASK
Implement a dedicated prediction service that evaluates risk markers and outputs structured confidence scores for {theme}.

## FILES TO CREATE
- `services/prediction_engine.py`: Encapsulates preprocessor, inference engine, and fallback heuristic model.
- `models/inference_schema.py`: Input feature schema and output risk classifications.

## TECHNICAL REQUIREMENTS
1. Support asynchronous inference with latency < 150ms.
2. If trained weights are missing, provide an intelligent rule-based heuristic fallback so the prototype never crashes during live judge demos.
3. Return output with confidence score (0.0 to 1.0) and top contributing feature factors.

## ACCEPTANCE CRITERIA
- Given raw domain inputs, returns risk level (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`) with confidence percentage."""

        prompts.append({
            "category": "AI/ML",
            "title": "Domain AI/ML Prediction & Confidence Scoring Engine",
            "prompt_text": prompt_ml,
            "target_tools": ["Cursor", "Claude Code", "Antigravity", "Gemini"]
        })

        # 3. Frontend Dashboard Prompt
        prompt_ui = f"""# PROMPT 3: INTERACTIVE DASHBOARD & USER INTERFACE
**Target Assistant:** Cursor / Claude Code / Antigravity / Gemini

## PROJECT CONTEXT
Repository `{repo_info.get('repo_name', 'project')}` targeting SIH Problem: **{ps_summary}**.
- Frontend Framework: {frontend}

## TASK
Build an interactive monitoring dashboard view that displays real-time telemetry metrics, risk heatmaps, status feeds, and critical alerts.

## FILES TO CREATE
- `components/DomainDashboard.jsx` (or HTML/JS component): Real-time metrics grid and chart container.
- `components/AlertNotificationPanel.jsx`: Toast/card feed for recent warnings.

## TECHNICAL REQUIREMENTS
1. Use dark modern glassmorphic styling consistent with the existing application design tokens.
2. Display summary KPI cards, interactive time-series chart, and status pill badges.
3. Handle loading, error, and empty states gracefully with subtle animations.

## ACCEPTANCE CRITERIA
- Dashboard renders live telemetry updates.
- Responsive across mobile, tablet, and desktop screens."""

        prompts.append({
            "category": "Frontend",
            "title": "Interactive Real-Time Monitoring Dashboard",
            "prompt_text": prompt_ui,
            "target_tools": ["Cursor", "Claude Code", "Antigravity", "Gemini"]
        })

        # 4. Database & Deployment Package Prompt
        prompt_deploy = f"""# PROMPT 4: DATABASE SCHEMA & DOCKER DEPLOYMENT PACKAGE
**Target Assistant:** Cursor / Claude Code / Antigravity / Gemini

## PROJECT CONTEXT
Packaging `{repo_info.get('repo_name', 'project')}` for SIH Hackathon Grand Finale Demonstration.

## TASK
Create containerization and reproducible database initialization files.

## FILES TO CREATE
- `docker-compose.yml`: Multi-container setup (Backend API + Database + Frontend).
- `Dockerfile`: Optimized multi-stage build.
- `scripts/seed_demo_data.py`: Pre-populates database with realistic SIH test records for offline judging demos.

## TECHNICAL REQUIREMENTS
1. Single command execution: `docker-compose up --build`.
2. Seed data script runs idempotently.

## ACCEPTANCE CRITERIA
- Full application stack boots with zero manual environment configuration."""

        prompts.append({
            "category": "Deployment",
            "title": "One-Command Docker Compose & Demo Seeding Package",
            "prompt_text": prompt_deploy,
            "target_tools": ["Cursor", "Claude Code", "Antigravity", "Gemini"]
        })

        return {
            "generated_prompts": prompts,
            "summary_output": f"Generated {len(prompts)} modular AI coding prompts ready for Cursor/Claude Code/Antigravity"
        }
