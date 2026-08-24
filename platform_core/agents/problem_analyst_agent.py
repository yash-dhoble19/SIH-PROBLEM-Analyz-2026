"""
Agent 5: Problem Statement Analyst.
Decomposes SIH problem statement into structured explicit vs inferred requirements and technical deliverables.
"""

import re
from typing import Dict, Any, List
from platform_core.agents.base import BaseAgent
from platform_core.database.models import ProblemStatement


class ProblemStatementAnalystAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 5: Problem Statement Analyst", ai_provider)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ps: ProblemStatement = context["problem_statement"]
        
        full_text = f"{ps.title}\n{ps.background or ''}\n{ps.description}\n{ps.expected_solution or ''}"
        
        # Extract requirements from bullet points or numbered lists
        explicit_requirements = []
        bullets = re.findall(r'(?:^|\n)\s*[•\-\*a-z0-9\.]\s*([A-Za-z0-9][^\n]{15,180})', full_text)
        for b in bullets:
            cleaned = b.strip()
            if not any(k in cleaned.lower() for k in ["background", "description", "expected solution", "http"]):
                explicit_requirements.append(cleaned)

        if not explicit_requirements:
            explicit_requirements = [
                f"Core functional system satisfying {ps.theme} requirements",
                "Automated data ingestion and real-time processing pipeline",
                "User-friendly web/mobile interface for authorities and citizens",
                "Scalable predictive or rule-based analytics engine",
                "Notification, reporting, and alert delivery mechanism"
            ]

        # Extract Technical Requirements
        tech_reqs = []
        if "gis" in full_text.lower() or "satellite" in full_text.lower() or "map" in full_text.lower():
            tech_reqs.append("Geospatial / GIS mapping & satellite imagery integration")
        if "ai" in full_text.lower() or "ml" in full_text.lower() or "model" in full_text.lower():
            tech_reqs.append("AI/ML model training, evaluation, and inference endpoints")
        if "real-time" in full_text.lower() or "live" in full_text.lower() or "sensor" in full_text.lower():
            tech_reqs.append("Real-time telemetry and streaming sensor ingestion")
        if "hardware" in ps.category.lower():
            tech_reqs.append("Hardware prototyping, firmware integration, and edge compute")
        tech_reqs.append("Reliable persistent relational database schema and REST APIs")

        return {
            "problem_summary": f"SIH {ps.id}: {ps.title} ({ps.organization})",
            "category": ps.category,
            "theme": ps.theme,
            "explicit_requirements": explicit_requirements[:8],
            "technical_requirements": tech_reqs,
            "data_requirements": [
                f"Domain datasets relevant to {ps.theme}",
                ps.dataset_link if ps.dataset_link else "Open government / sensor historical telemetry data"
            ],
            "judging_critical_capabilities": [
                "Real-world feasibility and deployment architecture",
                "Accuracy and responsiveness of detection/prediction",
                "Intuitive dashboard visualization for end-users",
                "Robust error handling and offline/low-connectivity resilience"
            ],
            "summary_output": f"Decomposed {ps.id} into {len(explicit_requirements[:8])} core requirements"
        }
