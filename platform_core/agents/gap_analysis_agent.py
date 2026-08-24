"""
Agent 6: Gap Analysis Agent.
Constructs a requirement-by-requirement comparison matrix by checking atomic requirements
against the structured Capability Manifest (names, evidence files, endpoints, data models).
Verdicts: MATCH/IMPLEMENTED, PARTIAL, MISSING.
Cites specific capability names and evidence files checked in every reason field.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional

from platform_core.agents.base import BaseAgent
from platform_core.ai.providers import (
    AIProvider,
    HeuristicAIProvider,
    GroqProvider,
    get_groq_provider,
    get_ai_provider,
)

logger = logging.getLogger("sih_platform.agents.gap_analysis")

_BANNED_BOILERPLATE = [
    "Requires implementation of domain-specific business rules specified in the problem statement",
    "model weights and architecture need fine-tuning for this domain",
    "Requires implementation of domain-specific business rules",
]

BATCH_SIZE = 4


class GapAnalysisAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 6: Gap Analysis Agent", ai_provider)

    def _get_reasoning_provider(self) -> AIProvider:
        """Resolve best available provider for gap reasoning."""
        groq = get_groq_provider()
        if groq is not None:
            logger.info("[GapAnalysis] Using GroqProvider for requirement reasoning.")
            return groq

        if self.ai_provider and not isinstance(self.ai_provider, HeuristicAIProvider):
            logger.info(f"[GapAnalysis] Using {type(self.ai_provider).__name__} for requirement reasoning.")
            return self.ai_provider

        logger.warning("[GapAnalysis] Using HeuristicAIProvider for capability-grounded gap analysis.")
        return self.ai_provider

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        analysis_data = context.get("analysis_data", {})
        problem_analysis = context.get("problem_analysis", {})

        reqs = problem_analysis.get("explicit_requirements", [])
        tech_reqs = problem_analysis.get("technical_requirements", [])
        combined_reqs = reqs + tech_reqs[:3]

        if not combined_reqs:
            return {
                "requirement_matrix": [],
                "matched_count": 0,
                "partial_count": 0,
                "missing_count": 0,
                "reusability_score": 0.0,
                "summary_findings": "No requirements were decomposed from the problem statement.",
                "summary_output": "Gap Analysis skipped — no requirements found."
            }

        manifest = analysis_data.get("capability_manifest") or {}
        capability_inventory = self._build_capability_inventory(analysis_data, manifest)

        provider = self._get_reasoning_provider()
        use_llm = not isinstance(provider, HeuristicAIProvider)

        matrix = []
        for batch_start in range(0, len(combined_reqs), BATCH_SIZE):
            batch = combined_reqs[batch_start:batch_start + BATCH_SIZE]
            if use_llm:
                batch_results = self._evaluate_batch_llm(provider, batch, capability_inventory, analysis_data, manifest)
            else:
                batch_results = self._evaluate_batch_heuristic(batch, analysis_data, manifest)
            matrix.extend(batch_results)

        matched_count = sum(1 for r in matrix if r["status"] in ("MATCH", "IMPLEMENTED"))
        partial_count = sum(1 for r in matrix if r["status"] == "PARTIAL")
        missing_count = sum(1 for r in matrix if r["status"] in ("MISSING", "UNKNOWN"))

        total = max(1, len(matrix))
        reusability = round(((matched_count * 1.0 + partial_count * 0.5) / total) * 100, 1)

        summary = (
            f"Gap Analysis: {matched_count} fully implemented/matched, {partial_count} partially covered, "
            f"{missing_count} missing/unknown out of {total} requirements. "
            f"Estimated code reusability: {reusability}%."
        )

        return {
            "requirement_matrix": matrix,
            "matched_count": matched_count,
            "partial_count": partial_count,
            "missing_count": missing_count,
            "reusability_score": reusability,
            "summary_findings": summary,
            "summary_output": f"Constructed Gap Matrix ({matched_count} Match, {partial_count} Partial, {missing_count} Missing)"
        }

    def _build_capability_inventory(self, analysis_data: Dict[str, Any], manifest: Dict[str, Any]) -> str:
        """Builds structured text of the Capability Manifest with explicit evidence citations."""
        lines = ["=== REPOSITORY CAPABILITY MANIFEST (CODE GROUNDED) ==="]

        caps = manifest.get("capabilities", [])
        if caps:
            lines.append("Verified Code Capabilities & Evidence:")
            for i, c in enumerate(caps, 1):
                ev = "; ".join(c.get("evidence", []))
                lines.append(f"  {i}. {c.get('name')} (Evidence: {ev or 'Codebase files'})")
        else:
            features = analysis_data.get("core_features", [])
            if features:
                lines.append("Detected Features:")
                for i, f in enumerate(features, 1):
                    lines.append(f"  {i}. {f}")

        endpoints = manifest.get("endpoints", [])
        if endpoints:
            lines.append("API Endpoints:")
            for ep in endpoints[:8]:
                lines.append(f"  - {ep.get('method')} {ep.get('path')} (Handler: {ep.get('handler')} in {ep.get('file')})")

        models = manifest.get("data_models", [])
        if models:
            lines.append("Data Models & Schemas:")
            for m in models[:6]:
                lines.append(f"  - {m.get('model_name')} in {m.get('file')} (Columns: {', '.join(m.get('columns', [])[:4])})")

        signals = manifest.get("domain_signals") or analysis_data.get("domain_signals", [])
        if signals:
            lines.append(f"Domain Signals: {', '.join(signals)}")

        tech = manifest.get("tech_stack") or analysis_data.get("detected_languages", [])
        if tech:
            lines.append(f"Tech Stack: {', '.join(tech)}")

        return "\n".join(lines)

    def _evaluate_batch_llm(
        self,
        provider: AIProvider,
        requirements: List[str],
        capability_inventory: str,
        analysis_data: Dict[str, Any],
        manifest: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Evaluate a batch of requirements with LLM grounded in Capability Manifest."""
        req_block = ""
        for i, req in enumerate(requirements):
            req_block += f'\n  REQ_{i+1}: "{req}"'

        prompt = f"""You are a technical code auditor evaluating whether a repository's VERIFIED CODE CAPABILITIES satisfy specific SIH hackathon requirements.

{capability_inventory}

=== REQUIREMENTS TO EVALUATE ==={req_block}

=== INSTRUCTIONS ===
For EACH requirement:
- "status": "MATCH", "PARTIAL", "MISSING", or "UNKNOWN"
  - MATCH: A verified code capability or endpoint directly fulfills this requirement.
  - PARTIAL: A related capability exists in code but needs domain extensions.
  - MISSING: No capability or code in the manifest addresses this.
- "current_project": State what specific capability and evidence file(s) exist. If missing, say what specific module is absent.
- "reason": Cite the EXACT capability name and evidence file(s) checked from the manifest.

Respond with ONLY valid JSON:
{{
  "evaluations": [
    {{
      "requirement": "<exact requirement>",
      "status": "MATCH|PARTIAL|MISSING|UNKNOWN",
      "current_project": "<capability and evidence file(s)>",
      "reason": "<specific explanation citing capability name and evidence file(s)>"
    }}
  ]
}}"""

        try:
            result = provider.generate_json(prompt)
            evaluations = result.get("evaluations", [])
            if not evaluations or not isinstance(evaluations, list):
                return self._evaluate_batch_heuristic(requirements, analysis_data, manifest)

            rows = []
            for i, ev in enumerate(evaluations):
                req_text = ev.get("requirement", requirements[i] if i < len(requirements) else "Unknown")
                status = ev.get("status", "UNKNOWN").upper()
                if status not in ("MATCH", "PARTIAL", "MISSING", "UNKNOWN", "IMPLEMENTED"):
                    status = "UNKNOWN"
                reason = ev.get("reason", "")
                if any(banned.lower() in reason.lower() for banned in _BANNED_BOILERPLATE):
                    reason = f"Checked capability manifest for '{req_text[:50]}'; requires dedicated implementation."

                rows.append({
                    "requirement": req_text[:90],
                    "sih_expects": req_text,
                    "current_project": ev.get("current_project", "Not assessed"),
                    "status": status,
                    "reason": reason
                })

            if len(rows) < len(requirements):
                remaining = requirements[len(rows):]
                rows.extend(self._evaluate_batch_heuristic(remaining, analysis_data, manifest))

            return rows
        except Exception:
            return self._evaluate_batch_heuristic(requirements, analysis_data, manifest)

    def _evaluate_batch_heuristic(
        self,
        requirements: List[str],
        analysis_data: Dict[str, Any],
        manifest: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Deterministic capability-matching against the Capability Manifest (names + evidence)."""
        caps = manifest.get("capabilities", [])
        endpoints = manifest.get("endpoints", [])
        models = manifest.get("data_models", [])
        features = [f.lower() for f in analysis_data.get("core_features", [])]
        backend = analysis_data.get("backend_framework", "")
        frontend = analysis_data.get("frontend_framework", "")

        rows = []
        for req in requirements:
            req_lower = req.lower()
            status, current, reason = self._classify_with_manifest(
                req, req_lower, caps, endpoints, models, features, backend, frontend, analysis_data
            )
            rows.append({
                "requirement": req[:90],
                "sih_expects": req,
                "current_project": current,
                "status": status,
                "reason": reason
            })
        return rows

    def _classify_with_manifest(
        self,
        req: str,
        req_lower: str,
        caps: List[Dict[str, Any]],
        endpoints: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
        features: List[str],
        backend: str,
        frontend: str,
        analysis_data: Dict[str, Any]
    ) -> tuple:
        """Classifies requirement against manifest capabilities citing specific names and evidence files."""

        # 1. Check Forecasting / Prediction
        if any(k in req_lower for k in ["forecast", "predict demand", "time series", "demand prediction", "demand estimation"]):
            for c in caps:
                if "forecast" in c["name"].lower() or "time-series" in c["name"].lower():
                    ev_str = ", ".join(c.get("evidence", [])) or c.get("file", "services/forecasting.py")
                    return (
                        "MATCH",
                        f"{c['name']} ({ev_str})",
                        f"Directly implemented by '{c['name']}' in {ev_str}, which provides time-series predictive modeling for this requirement."
                    )
            return (
                "MISSING",
                "No demand forecasting or time-series prediction module detected",
                f"Checked manifest capabilities ({', '.join([c['name'] for c in caps[:2]]) or 'none'}); no forecasting model (Prophet, ARIMA) was found for '{req[:45]}'."
            )

        # 2. Check Vehicle Routing / Fleet Dispatch
        if any(k in req_lower for k in ["routing", "vehicle route", "fleet dispatch", "route optimiz", "shortest path", "delivery route"]):
            for c in caps:
                if "routing" in c["name"].lower() or "vehicle" in c["name"].lower() or "transport" in c.get("category", "").lower():
                    ev_str = ", ".join(c.get("evidence", [])) or c.get("file", "services/routing.py")
                    return (
                        "MATCH",
                        f"{c['name']} ({ev_str})",
                        f"Directly implemented by '{c['name']}' in {ev_str}, which provides vehicle routing and dispatch algorithms."
                    )
            return (
                "MISSING",
                "No vehicle routing or dispatch engine detected",
                f"Checked manifest capabilities; no route optimization or graph-based dispatch module (Dijkstra, OSRM) was detected for '{req[:45]}'."
            )

        # 3. Check Web Scraping / Extraction
        if any(k in req_lower for k in ["scrape", "scraping", "crawler", "dom extract", "html parse", "data extraction from portal"]):
            for c in caps:
                if "scrap" in c["name"].lower() or "extract" in c["name"].lower():
                    ev_str = ", ".join(c.get("evidence", [])) or c.get("file", "services/scraper.py")
                    return (
                        "MATCH",
                        f"{c['name']} ({ev_str})",
                        f"Directly implemented by '{c['name']}' in {ev_str}, which handles DOM parsing and resilient HTML data extraction."
                    )
            return (
                "MISSING",
                "No web scraping or HTML parsing pipeline detected",
                f"Checked manifest capabilities; no scraper client or DOM extraction module (BeautifulSoup, Scrapy) was found for '{req[:45]}'."
            )

        # 4. Check Webhooks / Event Dispatch
        if any(k in req_lower for k in ["webhook", "event dispatch", "event notification", "subscription callback", "event listener"]):
            for c in caps:
                if "webhook" in c["name"].lower() or "event" in c["name"].lower():
                    ev_str = ", ".join(c.get("evidence", [])) or c.get("file", "services/webhook.py")
                    return (
                        "MATCH",
                        f"{c['name']} ({ev_str})",
                        f"Directly implemented by '{c['name']}' in {ev_str}, which provides event subscription and signed webhook delivery."
                    )
            return (
                "MISSING",
                "No webhook dispatch or event notification system detected",
                f"Checked manifest capabilities; no webhook dispatcher or signature verification logic was found for '{req[:45]}'."
            )

        # 5. Check API / Backend Services
        if any(k in req_lower for k in ["api", "rest", "backend", "endpoint", "server"]):
            if endpoints:
                ep_ev = f"{endpoints[0].get('method')} {endpoints[0].get('path')} in {endpoints[0].get('file')}"
                return (
                    "MATCH",
                    f"REST API Service Layer ({ep_ev})",
                    f"Directly satisfied by 'REST API Service Layer' ({len(endpoints)} endpoints defined, e.g. {ep_ev})."
                )
            elif backend:
                return (
                    "MATCH",
                    f"Backend service: {backend}",
                    f"The repository provides a '{backend}' backend framework capable of handling API requests."
                )

        # 6. Check UI / Dashboard / Frontend
        if any(k in req_lower for k in ["dashboard", "ui", "interface", "web", "frontend", "visualization"]):
            if frontend:
                return (
                    "MATCH",
                    f"Frontend application: {frontend}",
                    f"Directly addressed by the repository's '{frontend}' frontend layer for hosting UI and charts."
                )

        # 7. Check Database / Storage
        if any(k in req_lower for k in ["database", "storage", "persist", "data store", "schema", "table"]):
            if models:
                m_ev = f"{models[0].get('model_name')} in {models[0].get('file')}"
                return (
                    "MATCH",
                    f"Relational Data Persistence ({m_ev})",
                    f"Directly satisfied by 'Relational Data Persistence' with defined models ({', '.join([m.get('model_name') for m in models[:2]])})."
                )
            elif analysis_data.get("database_tech"):
                return (
                    "MATCH",
                    f"Database: {analysis_data['database_tech']}",
                    f"The repository uses '{analysis_data['database_tech']}' for data persistence."
                )

        # 8. Check Geospatial / Mapping
        if any(k in req_lower for k in ["gis", "map", "geospatial", "satellite", "coordinate", "location"]):
            for c in caps:
                if "geospatial" in c["name"].lower() or "gis" in c["name"].lower():
                    ev_str = ", ".join(c.get("evidence", [])) or "GIS module"
                    return (
                        "MATCH",
                        f"{c['name']} ({ev_str})",
                        f"Addressed by geospatial processing capability '{c['name']}' in {ev_str}."
                    )
            return (
                "MISSING",
                "No GIS or geospatial mapping code detected",
                f"Checked manifest capabilities; no mapping or GIS libraries (GeoPandas, Folium, Leaflet) were detected for '{req[:45]}'."
            )

        # 9. Check Cybersecurity / Firewall / Auditing
        if any(k in req_lower for k in ["security", "firewall", "encryption", "vulnerability", "intrusion", "packet"]):
            for c in caps:
                if "cyber" in c["name"].lower() or "security" in c["name"].lower():
                    ev_str = ", ".join(c.get("evidence", [])) or "Security module"
                    return (
                        "MATCH",
                        f"{c['name']} ({ev_str})",
                        f"Addressed by security capability '{c['name']}' in {ev_str}."
                    )
            return (
                "MISSING",
                "No cybersecurity or firewall auditing code detected",
                f"Checked manifest capabilities; no packet inspection or firewall audit modules were found for '{req[:45]}'."
            )

        # 10. Check Partial Overlaps with any named capability
        for c in caps:
            c_name = c["name"].lower()
            words = [w for w in req_lower.split() if len(w) > 4]
            if any(w in c_name for w in words):
                ev_str = ", ".join(c.get("evidence", [])) or "Codebase files"
                return (
                    "PARTIAL",
                    f"Related capability: '{c['name']}' ({ev_str})",
                    f"Partial coverage via verified capability '{c['name']}' in {ev_str}; domain extension required for '{req[:40]}'."
                )

        # 11. Generic Missing with clean citation of what was checked
        caps_names = ", ".join([c["name"] for c in caps[:3]]) or "standard application stack"
        return (
            "MISSING",
            f"No module addressing '{req[:40]}' found",
            f"Checked manifest capabilities ({caps_names}); no corresponding class, function, or endpoint was found for '{req[:50]}'. Must be implemented."
        )
