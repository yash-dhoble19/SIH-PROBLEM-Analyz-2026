"""
Agent 8: Implementation Planner Agent.
Creates a step-by-step phased roadmap identifying files to modify, files to create, complexity, and test plans.
"""

from typing import Dict, Any, List
from platform_core.agents.base import BaseAgent


class ImplementationPlannerAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 8: Implementation Planner Agent", ai_provider)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        analysis_data = context.get("analysis_data", {})
        problem_analysis = context.get("problem_analysis", {})
        arch_data = context.get("arch_data", {})
        
        ps_id = problem_analysis.get("problem_summary", "SIH Problem").split(":")[0]
        theme = problem_analysis.get("theme", "General")
        backend = analysis_data.get("backend_framework") or "FastAPI"
        frontend = analysis_data.get("frontend_framework") or "Web UI"
        detected_langs = analysis_data.get("detected_languages") or ["Python"]

        phases = [
            {
                "phase_number": 1,
                "title": "Phase 1: Domain Data Pipeline & Schema Migration",
                "why": f"SIH requires domain-specific data structures and historical datasets for {theme}.",
                "existing_status": "Basic data structures exist in the current project.",
                "required_changes": "Define database models for telemetry, sensor streams, incident logs, and user alerts.",
                "files_to_modify": ["models.py" if any("python" in l.lower() for l in detected_langs) else "schema.sql"],
                "files_to_create": ["domain_schema.py", "scripts/load_sih_data.py"],
                "complexity": "Medium",
                "testing": "Unit test database migrations and sample data fixture ingestion."
            },
            {
                "phase_number": 2,
                "title": "Phase 2: AI/ML Inference & Prediction Engine",
                "why": "Provide automated detection, risk ranking, or anomaly recognition as required by SIH.",
                "existing_status": "Existing ML baseline / data algorithms present in repo.",
                "required_changes": "Implement trained model wrapper, feature preprocessor, and confidence scoring pipeline.",
                "files_to_modify": ["main.py" if backend == "FastAPI" else "app.py"],
                "files_to_create": ["services/prediction_engine.py", "models/trained_weights.pkl"],
                "complexity": "High",
                "testing": "Validate precision, recall, and benchmark inference latency under 200ms."
            },
            {
                "phase_number": 3,
                "title": "Phase 3: Backend REST APIs & Real-Time Alert Engine",
                "why": "Allow client applications to query live risk metrics, trigger alerts, and receive updates.",
                "existing_status": f"{backend} routing framework is configured.",
                "required_changes": "Add endpoints for live telemetry ingestion, risk evaluation, and automated alert dispatch.",
                "files_to_modify": ["routes.py" if "routes" in str(analysis_data.get("api_routes", [])) else "app.py"],
                "files_to_create": ["routers/sih_analytics.py", "services/alert_dispatcher.py"],
                "complexity": "Medium",
                "testing": "Integration tests asserting 200 OK responses on all analytics endpoints."
            },
            {
                "phase_number": 4,
                "title": "Phase 4: Frontend Interactive Dashboard & Visualization",
                "why": "Present authorities and stakeholders with real-time risk heatmaps, status feeds, and control panels.",
                "existing_status": f"{frontend} client application exists.",
                "required_changes": "Create dedicated dashboard component with live telemetry graphs, risk heatmaps, and alert toasts.",
                "files_to_modify": ["App.js" if "React" in frontend else "index.html"],
                "files_to_create": ["src/components/RiskDashboard.jsx", "src/components/AlertPanel.jsx"],
                "complexity": "Medium",
                "testing": "End-to-end browser walkthrough testing user interactions and live chart rendering."
            },
            {
                "phase_number": 5,
                "title": "Phase 5: Containerization, Testing & Hackathon Demo Package",
                "why": "Enable reliable, one-command deployment for SIH grand finale judging demonstrations.",
                "existing_status": "Repository files indexed.",
                "required_changes": "Create multi-stage Dockerfile, docker-compose.yml with persistent DB, and demo seed data script.",
                "files_to_modify": ["README.md"],
                "files_to_create": ["Dockerfile", "docker-compose.yml", "demo_scenario.sh"],
                "complexity": "Low",
                "testing": "Execute docker-compose up --build and test complete end-to-end demonstration flow."
            }
        ]

        return {
            "phases": phases,
            "architecture_overview": arch_data.get("architecture_overview", ""),
            "estimated_effort": "2 to 3 days for complete prototype delivery",
            "summary_output": f"Generated 5-Phase Implementation Roadmap ({phases[0]['title']} -> {phases[-1]['title']})"
        }
