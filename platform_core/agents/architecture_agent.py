"""
Agent 3: Technology & Architecture Agent.
Evaluates architecture patterns, layer modularity, database design, and tech stack robustness.
"""

from typing import Dict, Any, List
from platform_core.agents.base import BaseAgent


class TechnologyArchitectureAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 3: Technology & Architecture Agent", ai_provider)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        static = context.get("static_analysis", {})
        
        backend = static.get("backend_framework")
        frontend = static.get("frontend_framework")
        db_tech = static.get("database_tech")
        ml_caps = static.get("ml_capabilities", [])
        
        strengths = []
        limitations = []

        if backend:
            strengths.append(f"Structured backend services powered by {backend}")
        else:
            limitations.append("No explicit dedicated web API framework detected")

        if frontend:
            strengths.append(f"Modern client UI layer utilizing {frontend}")
        
        if db_tech:
            strengths.append(f"Persistent relational/document storage using {db_tech}")
        else:
            limitations.append("Lacks integrated persistent database schema")

        if ml_caps:
            strengths.append(f"AI/ML pipeline integrations: {', '.join(ml_caps)}")

        if "Docker" in static.get("detected_frameworks", []):
            strengths.append("Containerized development and reproducible deployment workflow")

        return {
            "backend_framework": backend,
            "frontend_framework": frontend,
            "database_tech": db_tech,
            "architectural_strengths": strengths,
            "limitations": limitations,
            "summary_output": f"Architecture analysis: {len(strengths)} strengths, {len(limitations)} potential gaps"
        }
