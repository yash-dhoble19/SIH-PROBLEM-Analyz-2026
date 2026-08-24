"""
Agent 10: Pivot Advisor Agent.
Answers "what would it take to transform this project to satisfy this problem statement".
Strictly distinct from the Gap Analysis Agent ("what's missing today").

Trigger Condition:
Runs ONLY when 15.0% <= domain_alignment_score <= 100.0% AND reusability_score < 80.0%.
Otherwise returns None / empty analysis.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from platform_core.agents.base import BaseAgent

logger = logging.getLogger("sih_platform.agents.pivot_advisor")


class PivotAdvisorAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 10: Pivot Advisor Agent", ai_provider)

    def should_trigger(self, domain_alignment: float, reusability_score: float) -> bool:
        """
        Determines if the Pivot Advisor should run.
        Skip when domain alignment is negligible (< 15%) or when project is already near-perfect (>= 80%).
        """
        return (domain_alignment >= 15.0) and (reusability_score < 80.0)

    def run(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        domain_alignment = float(context.get("domain_alignment", 0.0))
        reusability_score = float(context.get("reusability_score", 0.0))

        # Check trigger condition
        if not self.should_trigger(domain_alignment, reusability_score):
            logger.info(
                f"PivotAdvisor skipped: domain_alignment={domain_alignment}%, reusability={reusability_score}% "
                f"(Requires 15% <= domain_alignment AND reusability < 80%)"
            )
            return None

        capability_manifest = context.get("capability_manifest") or {}
        requirement_matrix = context.get("requirement_matrix") or []
        problem_statement = context.get("problem_statement") or {}
        analysis_data = context.get("analysis_data") or {}
        repo_info = context.get("repo_info") or {}

        # 1. Extract Reusable Foundations
        reused_foundations = self._extract_reused_foundations(
            capability_manifest=capability_manifest,
            requirement_matrix=requirement_matrix,
            problem_statement=problem_statement
        )

        # 2. Extract Required Additions
        required_additions = self._extract_required_additions(
            requirement_matrix=requirement_matrix,
            problem_statement=problem_statement,
            analysis_data=analysis_data
        )

        # 3. Generate Transformation Summary
        transformation_summary = self._generate_transformation_summary(
            reused_count=len(reused_foundations),
            additions_count=len(required_additions),
            problem_title=problem_statement.get("title", "SIH Problem Statement"),
            reusability_score=reusability_score
        )

        # 4. Generate LLM Copy-Paste Coding Prompt for Additions
        copy_paste_prompt = self._construct_pivot_coding_prompt(
            repo_info=repo_info,
            problem_statement=problem_statement,
            analysis_data=analysis_data,
            reused_foundations=reused_foundations,
            required_additions=required_additions
        )

        return {
            "is_applicable": True,
            "domain_alignment": domain_alignment,
            "reusability_score": reusability_score,
            "transformation_summary": transformation_summary,
            "reused_foundations": reused_foundations,
            "required_additions": required_additions,
            "copy_paste_prompt": copy_paste_prompt,
            "summary_output": f"Generated Pivot Strategy: {len(reused_foundations)} reusable foundations, {len(required_additions)} required additions"
        }

    def _extract_reused_foundations(
        self,
        capability_manifest: Dict[str, Any],
        requirement_matrix: List[Dict[str, Any]],
        problem_statement: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identifies existing capabilities/files that genuinely transfer with a concrete reuse mechanism."""
        foundations = []
        seen_caps = set()

        # Check existing AST capabilities
        capabilities = capability_manifest.get("capabilities", [])
        endpoints = capability_manifest.get("endpoints", [])
        data_models = capability_manifest.get("data_models", [])

        # Add match/partial items from requirement matrix
        for item in requirement_matrix:
            if item.get("status") in ("MATCH", "PARTIAL"):
                cap_name = item.get("requirement", "Existing Subsystem")
                reason = item.get("reason", "")
                if cap_name not in seen_caps:
                    seen_caps.add(cap_name)
                    foundations.append({
                        "capability": cap_name,
                        "source_evidence": item.get("current_project", "Existing Repository Component"),
                        "reuse_mechanism": f"Directly repurpose for {problem_statement.get('theme', 'the target domain')}: {reason}"
                    })

        # Add API / Backend service layer if present
        if endpoints and "REST API Layer" not in seen_caps:
            seen_caps.add("REST API Layer")
            endpoint_sample = ", ".join([f"{e.get('method')} {e.get('path')}" for e in endpoints[:3]])
            foundations.append({
                "capability": "HTTP API Service Layer",
                "source_evidence": f"Endpoints: {endpoint_sample}",
                "reuse_mechanism": f"Extend existing API routing and dependency injection patterns to mount new {problem_statement.get('theme', 'domain')} endpoints without rebuilding the server harness."
            })

        # Add Data models / ORM layer if present
        if data_models and "Data Persistence Layer" not in seen_caps:
            seen_caps.add("Data Persistence Layer")
            models_sample = ", ".join([m.get("model_name", "") for m in data_models[:3]])
            foundations.append({
                "capability": "Relational Data Modeling & Persistence",
                "source_evidence": f"ORM Models: {models_sample}",
                "reuse_mechanism": "Leverage existing database session management and schema migrations to attach new domain entity tables."
            })

        # Fallback if sparse
        if not foundations:
            for cap in capabilities[:3]:
                foundations.append({
                    "capability": cap.get("name", "Core Component"),
                    "source_evidence": "; ".join(cap.get("evidence", [])) or "Codebase source files",
                    "reuse_mechanism": f"Adapt pipeline logic to process telemetry and domain schemas for {problem_statement.get('title', 'SIH problem')}."
                })

        return foundations

    def _extract_required_additions(
        self,
        requirement_matrix: List[Dict[str, Any]],
        problem_statement: Dict[str, Any],
        analysis_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identifies net-new features needed with priority, effort, build approach, and integration target."""
        additions = []
        backend = analysis_data.get("backend_framework") or "Backend API"

        # Extract from MISSING / PARTIAL items in gap matrix
        missing_items = [r for r in requirement_matrix if r.get("status") in ("MISSING", "PARTIAL")]
        
        priority_map = {0: "P0 - Critical", 1: "P0 - Critical", 2: "P1 - High", 3: "P1 - High", 4: "P2 - Medium"}
        effort_map = {0: "1-2 days", 1: "2-3 days", 2: "1 day", 3: "1-2 days", 4: "4-8 hours"}

        for idx, item in enumerate(missing_items[:5]):
            req_name = item.get("requirement", f"Required Feature {idx+1}")
            expects = item.get("sih_expects", "Domain capability required by problem statement")
            
            # Determine build approach and integration target
            if "api" in req_name.lower() or "endpoint" in req_name.lower() or "backend" in req_name.lower():
                build_approach = f"Implement new async route handlers in `{backend}` adhering to OpenAPI schema specifications."
                integration_target = "Main application router / dependency injection container"
            elif "model" in req_name.lower() or "ai" in req_name.lower() or "predict" in req_name.lower() or "ml" in req_name.lower():
                build_approach = "Develop an isolated inference/heuristic engine with rule-based fallback and confidence scoring."
                integration_target = "Services layer (`services/` or `core/` pipeline)"
            elif "dashboard" in req_name.lower() or "ui" in req_name.lower() or "interface" in req_name.lower():
                build_approach = "Construct responsive visualization panels displaying real-time metrics, status filters, and export controls."
                integration_target = "Frontend view layer (`static/` or UI components)"
            else:
                build_approach = f"Build modular domain service logic satisfying: {expects}"
                integration_target = f"Core business logic modules in `{backend}`"

            additions.append({
                "feature": req_name,
                "priority": priority_map.get(idx, "P2 - Medium"),
                "effort_estimate": effort_map.get(idx, "1-2 days"),
                "why_needed": f"Required to fulfill SIH criteria: {expects}",
                "build_approach": build_approach,
                "integration_target": integration_target
            })

        # If gap matrix was empty, populate from problem statement expected solution
        if not additions:
            expected_sol = problem_statement.get("expected_solution") or problem_statement.get("description") or "Domain workflow solution"
            additions.append({
                "feature": f"{problem_statement.get('theme', 'Domain')} Core Processing Pipeline",
                "priority": "P0 - Critical",
                "effort_estimate": "2-3 days",
                "why_needed": f"Fulfills expected solution: {expected_sol[:120]}...",
                "build_approach": f"Create specialized business logic service integrated with existing `{backend}` framework.",
                "integration_target": "Services / Controllers layer"
            })

        return additions

    def _generate_transformation_summary(
        self,
        reused_count: int,
        additions_count: int,
        problem_title: str,
        reusability_score: float
    ) -> str:
        return (
            f"To pivot this repository for '{problem_title}', you can reuse {reused_count} existing architectural foundation(s) "
            f"({reusability_score:.1f}% reusability) while implementing {additions_count} net-new domain feature(s). "
            f"This transformation allows you to build upon tested code rather than starting from scratch."
        )

    def _construct_pivot_coding_prompt(
        self,
        repo_info: Dict[str, Any],
        problem_statement: Dict[str, Any],
        analysis_data: Dict[str, Any],
        reused_foundations: List[Dict[str, Any]],
        required_additions: List[Dict[str, Any]]
    ) -> str:
        """Constructs an actionable copy-paste prompt formatted for Cursor / Claude Code / Antigravity."""
        repo_name = repo_info.get("repo_name", "project")
        ps_id = problem_statement.get("id", "SIH2026")
        ps_title = problem_statement.get("title", "Problem Statement")
        ps_org = problem_statement.get("organization", "SIH Ministry / Organization")
        ps_theme = problem_statement.get("theme", "Domain Theme")
        backend = analysis_data.get("backend_framework", "Backend Framework")
        detected_langs = ", ".join(analysis_data.get("detected_languages", ["Python"]))

        foundations_text = ""
        for idx, rf in enumerate(reused_foundations, 1):
            foundations_text += f"{idx}. **{rf['capability']}**\n   - *Evidence:* `{rf['source_evidence']}`\n   - *Reuse Strategy:* {rf['reuse_mechanism']}\n"

        additions_text = ""
        for idx, ra in enumerate(required_additions, 1):
            additions_text += (
                f"{idx}. **{ra['feature']}** `[{ra['priority']}]` (Effort: {ra['effort_estimate']})\n"
                f"   - *Why Needed:* {ra['why_needed']}\n"
                f"   - *Build Approach:* {ra['build_approach']}\n"
                f"   - *Integration Target:* `{ra['integration_target']}`\n"
            )

        prompt = f"""# REPOSITORY PIVOT TRANSFORMATION PROMPT
**Target Assistant:** Cursor / Claude Code / Antigravity / Gemini
**Target Problem Statement:** {ps_id} — {ps_title}
**Organization / Ministry:** {ps_org} | **Theme:** {ps_theme}

## OBJECTIVE
Transform the existing repository `{repo_name}` ({detected_langs}, {backend}) to fully satisfy the Smart India Hackathon problem statement **{ps_title}** by building upon its existing verified architecture.

---

## 1. REUSABLE ARCHITECTURAL FOUNDATIONS (PRESERVE & EXTEND)
Do NOT rewrite or discard the following components; leverage and extend them:
{foundations_text or "Preserve existing routing, database connection, and utility services."}

---

## 2. REQUIRED NET-NEW ADDITIONS (BUILD IN ORDER)
Implement the following new modules, integrating cleanly with the existing code patterns:
{additions_text}

---

## 3. IMPLEMENTATION INSTRUCTIONS
1. **Preserve Compatibility:** Ensure all existing unit tests and core modules continue to pass.
2. **Schema Validation:** Use strict Pydantic / dataclass schemas for all new domain endpoints.
3. **Resilient Defaults:** Provide heuristic or mock fallbacks so the prototype runs reliably in offline judge presentations.
4. **Integration Testing:** Add targeted unit tests for the newly added domain services in `tests/`.

---

## CRITICAL RULE
Do NOT start from scratch or wipe existing directories. Mount the new domain capabilities directly into `{repo_name}` following its established architectural conventions."""

        return prompt.strip()
