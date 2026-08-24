"""
Agent 6: Gap Analysis Agent.
Constructs a requirement-by-requirement comparison matrix by making grounded LLM calls
(batched 3-5 requirements per call) that reference the EXACT requirement text and the
repo's SPECIFIC detected capabilities.

Provider priority: Groq (free tier) -> General AI provider -> Heuristic (last resort, logged loudly).
"""

import json
import logging
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

# The old boilerplate strings that must NEVER appear in output
_BANNED_BOILERPLATE = [
    "Requires implementation of domain-specific business rules specified in the problem statement",
    "model weights and architecture need fine-tuning for this domain",
    "Requires implementation of domain-specific business rules",
]

BATCH_SIZE = 4  # Requirements per LLM call — keeps within Groq free-tier token budget


class GapAnalysisAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 6: Gap Analysis Agent", ai_provider)

    def _get_reasoning_provider(self) -> AIProvider:
        """
        Resolve the best available provider for gap reasoning.
        Priority: Groq (free, fast) -> configured AI provider -> Heuristic (loud warning).
        """
        # 1. Try dedicated Groq provider first
        groq = get_groq_provider()
        if groq is not None:
            logger.info("[GapAnalysis] Using GroqProvider (openai/gpt-oss-120b) for requirement reasoning.")
            return groq

        # 2. Fall back to whatever the base class resolved (Anthropic/OpenAI/Gemini)
        if self.ai_provider and not isinstance(self.ai_provider, HeuristicAIProvider):
            logger.info(f"[GapAnalysis] Using {type(self.ai_provider).__name__} for requirement reasoning.")
            return self.ai_provider

        # 3. Absolute last resort — log loudly
        logger.warning(
            "⚠️  [GapAnalysis] NO real LLM provider available (no Groq/Anthropic/OpenAI key). "
            "Falling back to HeuristicAIProvider — gap analysis reasons will be keyword-derived, "
            "NOT LLM-grounded. Set GROQ_API_KEY in .env for free high-quality reasoning."
        )
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

        # Build the full repo capability inventory for the LLM prompt
        capability_inventory = self._build_capability_inventory(analysis_data)

        # Resolve the best available reasoning provider
        provider = self._get_reasoning_provider()
        use_llm = not isinstance(provider, HeuristicAIProvider)

        # Batch requirements and evaluate
        matrix = []
        for batch_start in range(0, len(combined_reqs), BATCH_SIZE):
            batch = combined_reqs[batch_start:batch_start + BATCH_SIZE]
            if use_llm:
                batch_results = self._evaluate_batch_llm(provider, batch, capability_inventory, analysis_data)
            else:
                batch_results = self._evaluate_batch_heuristic(batch, analysis_data)
            matrix.extend(batch_results)

        # Count statuses
        matched_count = sum(1 for r in matrix if r["status"] == "MATCH")
        partial_count = sum(1 for r in matrix if r["status"] == "PARTIAL")
        missing_count = sum(1 for r in matrix if r["status"] in ("MISSING", "UNKNOWN"))

        total = max(1, len(matrix))
        reusability = round(((matched_count * 1.0 + partial_count * 0.5) / total) * 100, 1)

        summary = (
            f"Gap Analysis: {matched_count} fully matched, {partial_count} partially covered, "
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

    def _build_capability_inventory(self, analysis_data: Dict[str, Any]) -> str:
        """Build a detailed, enumerated text block of all detected repo capabilities."""
        lines = []
        lines.append("=== REPOSITORY DETECTED CAPABILITIES ===")

        langs = analysis_data.get("detected_languages", [])
        if langs:
            lines.append(f"Programming Languages: {', '.join(langs)}")

        backend = analysis_data.get("backend_framework")
        if backend:
            lines.append(f"Backend Framework: {backend}")

        frontend = analysis_data.get("frontend_framework")
        if frontend:
            lines.append(f"Frontend Framework: {frontend}")

        db_tech = analysis_data.get("database_tech")
        if db_tech:
            lines.append(f"Database Technology: {db_tech}")

        ml_caps = analysis_data.get("ml_capabilities", [])
        if ml_caps:
            lines.append(f"ML/AI Libraries: {', '.join(ml_caps)}")

        features = analysis_data.get("core_features", [])
        if features:
            lines.append("Detected Features:")
            for i, f in enumerate(features, 1):
                lines.append(f"  {i}. {f}")

        tech_caps = analysis_data.get("technical_capabilities", [])
        if tech_caps:
            lines.append("Technical Capabilities:")
            for i, c in enumerate(tech_caps, 1):
                lines.append(f"  {i}. {c}")

        strengths = analysis_data.get("architectural_strengths", [])
        if strengths:
            lines.append("Architectural Strengths:")
            for i, s in enumerate(strengths, 1):
                lines.append(f"  {i}. {s}")

        api_routes = analysis_data.get("api_routes", [])
        if api_routes:
            lines.append(f"API Routes: {', '.join(str(r) for r in api_routes[:10])}")

        project_type = analysis_data.get("project_type")
        if project_type:
            lines.append(f"Project Type: {project_type}")

        summary = analysis_data.get("project_summary")
        if summary:
            lines.append(f"Project Purpose: {summary}")

        if len(lines) <= 1:
            lines.append("No specific capabilities detected — generic software project.")

        return "\n".join(lines)

    def _evaluate_batch_llm(
        self,
        provider: AIProvider,
        requirements: List[str],
        capability_inventory: str,
        analysis_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Send a batch of 3-5 requirements to the LLM in a single call.
        Each requirement gets its own independent status + reason in the response.
        """
        req_block = ""
        for i, req in enumerate(requirements):
            req_block += f'\n  REQ_{i+1}: "{req}"'

        prompt = f"""You are evaluating whether a GitHub repository's ACTUAL detected capabilities can satisfy specific SIH hackathon problem statement requirements.

{capability_inventory}

=== REQUIREMENTS TO EVALUATE ==={req_block}

=== INSTRUCTIONS ===
For EACH requirement above, determine:
- "status": one of "MATCH", "PARTIAL", "MISSING", or "UNKNOWN"
  - MATCH: The repo has a specific, detected capability that directly addresses this requirement.
  - PARTIAL: The repo has related capability that partially covers this, but specific extensions are needed.
  - MISSING: The repo has NO detected capability related to this requirement.
  - UNKNOWN: Cannot determine from the available capability data.
- "current_project": What the repo currently has that relates to this requirement. If nothing, say exactly what's absent (e.g. "No firewall/packet inspection code detected").
- "reason": A SPECIFIC explanation that:
  1. Names the EXACT repo capability (if any) that relates to this requirement — quote from the capability inventory above.
  2. Explains CONCRETELY what gap exists (e.g. "No SNMP/router config parsing library detected" NOT "requires domain-specific business rules").
  3. Must be DIFFERENT for each requirement — never copy-paste the same reason across rows.

Respond with ONLY this JSON (no markdown fences):
{{
  "evaluations": [
    {{
      "requirement": "<exact requirement text>",
      "status": "MATCH|PARTIAL|MISSING|UNKNOWN",
      "current_project": "<what repo has or lacks for this>",
      "reason": "<specific, grounded explanation>"
    }}
  ]
}}"""

        system_prompt = (
            "You are a strict technical auditor comparing a repository's actual codebase capabilities "
            "against hackathon requirements. Never use generic boilerplate. Every reason must reference "
            "specific detected (or missing) capabilities from the repository inventory provided."
        )

        try:
            result = provider.generate_json(prompt, system_prompt=system_prompt)
            evaluations = result.get("evaluations", [])

            if not evaluations or not isinstance(evaluations, list):
                logger.error(f"[GapAnalysis] LLM returned malformed evaluations: {result}")
                return self._evaluate_batch_heuristic(requirements, analysis_data)

            rows = []
            for i, ev in enumerate(evaluations):
                req_text = ev.get("requirement", requirements[i] if i < len(requirements) else "Unknown")
                status = ev.get("status", "UNKNOWN").upper()
                if status not in ("MATCH", "PARTIAL", "MISSING", "UNKNOWN"):
                    status = "UNKNOWN"

                reason = ev.get("reason", "")
                # Guard: reject any banned boilerplate that leaked through
                if any(banned.lower() in reason.lower() for banned in _BANNED_BOILERPLATE):
                    reason = f"[Flagged generic] Requirement '{req_text[:50]}...' needs specific analysis — no matching capability was clearly identified in the repository."

                rows.append({
                    "requirement": req_text[:90],
                    "sih_expects": req_text,
                    "current_project": ev.get("current_project", "Not assessed"),
                    "status": status,
                    "reason": reason
                })

            # If LLM returned fewer evaluations than we sent, fill remaining with heuristic
            if len(rows) < len(requirements):
                remaining = requirements[len(rows):]
                rows.extend(self._evaluate_batch_heuristic(remaining, analysis_data))

            return rows

        except json.JSONDecodeError as e:
            logger.error(f"[GapAnalysis] LLM returned invalid JSON: {e}. Falling back to heuristic for this batch.")
            return self._evaluate_batch_heuristic(requirements, analysis_data)
        except Exception as e:
            logger.error(f"[GapAnalysis] LLM call failed: {e}. Falling back to heuristic for this batch.")
            return self._evaluate_batch_heuristic(requirements, analysis_data)

    def _evaluate_batch_heuristic(
        self,
        requirements: List[str],
        analysis_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Deterministic keyword-grounded fallback. Each requirement gets a SPECIFIC reason
        that names what's present or absent — never a generic template.
        """
        features = [f.lower() for f in analysis_data.get("core_features", [])]
        ml_caps = [m.lower() for m in analysis_data.get("ml_capabilities", [])]
        backend = analysis_data.get("backend_framework", "")
        frontend = analysis_data.get("frontend_framework", "")
        all_caps_text = " ".join(features + ml_caps).lower()

        rows = []
        for req in requirements:
            req_lower = req.lower()
            status, current, reason = self._classify_requirement_heuristic(
                req, req_lower, features, ml_caps, backend, frontend, all_caps_text, analysis_data
            )
            rows.append({
                "requirement": req[:90],
                "sih_expects": req,
                "current_project": current,
                "status": status,
                "reason": reason
            })
        return rows

    def _classify_requirement_heuristic(
        self, req: str, req_lower: str,
        features: list, ml_caps: list,
        backend: str, frontend: str,
        all_caps_text: str, analysis_data: Dict[str, Any]
    ) -> tuple:
        """Classify a single requirement using keyword matching with SPECIFIC reasons."""

        # --- MATCH checks ---
        if any(k in req_lower for k in ["api", "rest", "backend", "server", "endpoint"]) and backend:
            return (
                "MATCH",
                f"Backend service: {backend}",
                f"The repository provides '{backend}' backend with API endpoint handling, which directly addresses this requirement."
            )

        if any(k in req_lower for k in ["dashboard", "ui", "interface", "web", "frontend", "visualization"]) and frontend:
            return (
                "MATCH",
                f"Frontend application: {frontend}",
                f"The repository includes a '{frontend}' frontend layer capable of hosting the required user interface components."
            )

        if any(k in req_lower for k in ["database", "storage", "persist", "data store"]):
            db_tech = analysis_data.get("database_tech")
            if db_tech:
                return (
                    "MATCH",
                    f"Database: {db_tech}",
                    f"The repository uses '{db_tech}' for persistent storage, satisfying this data management requirement."
                )

        # --- PARTIAL checks ---
        if any(k in req_lower for k in ["ai", "ml", "model", "prediction", "detection", "classification", "neural"]):
            if ml_caps:
                caps_str = ", ".join(analysis_data.get("ml_capabilities", [])[:3])
                return (
                    "PARTIAL",
                    f"ML libraries detected: {caps_str}",
                    f"The repository includes ML libraries ({caps_str}) but no pre-trained model or training pipeline "
                    f"specific to '{req[:50]}' was detected. Domain-specific model development is needed."
                )
            else:
                return (
                    "MISSING",
                    "No ML/AI libraries or models detected in the repository",
                    f"This requirement needs AI/ML capabilities ('{req[:50]}') but no ML frameworks "
                    f"(PyTorch, TensorFlow, scikit-learn, etc.) were found in the repository dependencies."
                )

        if any(k in req_lower for k in ["real-time", "streaming", "websocket", "live", "telemetry"]):
            if backend:
                return (
                    "PARTIAL",
                    f"Async-capable backend ({backend}) but no WebSocket/streaming module detected",
                    f"The '{backend}' backend can handle async requests, but dedicated real-time streaming "
                    f"infrastructure (WebSockets, Server-Sent Events, or message queues) was not detected."
                )
            return (
                "MISSING",
                "No real-time streaming or WebSocket infrastructure detected",
                f"This requirement needs real-time data streaming but no backend framework or "
                f"WebSocket handler was found in the repository."
            )

        if any(k in req_lower for k in ["alert", "notification", "sms", "email", "push"]):
            return (
                "MISSING",
                "No notification dispatch system detected (no SMS/email/push libraries found)",
                f"This requirement needs alert/notification delivery but no SMS gateway (Twilio), "
                f"email service (SendGrid), or push notification library was detected in the repository."
            )

        if any(k in req_lower for k in ["gis", "map", "geospatial", "satellite", "coordinate", "location"]):
            if any("gis" in c or "geo" in c or "map" in c for c in features + ml_caps):
                return (
                    "MATCH",
                    "Geospatial/mapping components detected",
                    "The repository includes geospatial processing capabilities that address this mapping requirement."
                )
            return (
                "MISSING",
                "No GIS, mapping, or geospatial libraries detected (no Leaflet, Mapbox, GeoPandas, etc.)",
                f"This requirement needs geospatial/mapping capabilities but no GIS libraries "
                f"(GeoPandas, Folium, Leaflet, Mapbox) were found in the repository."
            )

        if any(k in req_lower for k in ["security", "firewall", "encryption", "auth", "vulnerability", "intrusion"]):
            if any("security" in c or "auth" in c or "encrypt" in c for c in features):
                return (
                    "PARTIAL",
                    "Basic authentication/security detected",
                    f"The repository has basic auth/security features but no specialized security "
                    f"tooling for '{req[:40]}' (no vulnerability scanner, SIEM, or firewall SDK) was detected."
                )
            return (
                "MISSING",
                "No cybersecurity, firewall, or network security code detected",
                f"This requirement needs security/firewall capabilities but no security-specific libraries "
                f"(packet inspection, SIEM integration, firewall SDKs) were found in the repository."
            )

        if any(k in req_lower for k in ["hardware", "firmware", "iot", "sensor", "embedded", "microcontroller"]):
            return (
                "MISSING",
                "Software-only codebase — no hardware/IoT/embedded code detected",
                f"This requirement needs hardware/IoT integration but the repository is a pure software "
                f"project with no embedded systems, firmware, or sensor interface code detected."
            )

        if any(k in req_lower for k in ["network", "packet", "router", "switch", "protocol", "tcp", "udp", "snmp"]):
            return (
                "MISSING",
                "No networking/packet analysis or protocol handling code detected",
                f"This requirement needs network protocol handling but no networking libraries "
                f"(Scapy, socket programming, SNMP, pcap) were found in the repository."
            )

        # --- Fallback: try to find ANY feature overlap ---
        for feat in features:
            # Check if any words from the requirement appear in this feature
            req_words = [w for w in req_lower.split() if len(w) > 4]
            if any(w in feat for w in req_words):
                return (
                    "PARTIAL",
                    f"Potentially related feature: '{feat}'",
                    f"The repository feature '{feat}' has partial keyword overlap with this requirement, "
                    f"but dedicated implementation for '{req[:40]}' was not confirmed."
                )

        # Genuine unknown — but with a SPECIFIC reason, not generic boilerplate
        return (
            "MISSING",
            f"No capability matching '{req[:40]}' detected in repository",
            f"No repository feature, library, or module was identified that addresses "
            f"'{req[:60]}'. This functionality would need to be built from scratch."
        )
