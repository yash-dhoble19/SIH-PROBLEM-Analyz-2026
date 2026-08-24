"""
Multi-Agent Orchestrator Pipeline.
Executes the end-to-end repository analysis, pgvector matching, gap analysis, and prompt generation
with code-grounded Capability Manifest propagation.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from platform_core.database.models import (
    Repository,
    RepositoryFile,
    RepositoryAnalysis,
    ProblemMatch,
    GapAnalysis,
    ImplementationPlan,
    GeneratedPrompt,
    ProblemStatement,
    AnalysisJob
)
from platform_core.github.client import GitHubClient
from platform_core.github.analyzer import RepositoryStaticAnalyzer
from platform_core.agents.explorer_agent import RepositoryExplorerAgent
from platform_core.agents.understanding_agent import ProjectUnderstandingAgent
from platform_core.agents.architecture_agent import TechnologyArchitectureAgent
from platform_core.agents.matching_agent import SIHMatchingAgent
from platform_core.agents.problem_analyst_agent import ProblemStatementAnalystAgent
from platform_core.agents.gap_analysis_agent import GapAnalysisAgent
from platform_core.agents.solution_architect_agent import SolutionArchitectAgent
from platform_core.agents.implementation_planner_agent import ImplementationPlannerAgent
from platform_core.agents.prompt_generator_agent import PromptGeneratorAgent
from platform_core.agents.pivot_advisor_agent import PivotAdvisorAgent

logger = logging.getLogger("sih_platform.orchestrator")


class MultiAgentPipeline:
    """Coordinates static analysis, vector matching, and agent reasoning pipelines."""

    def __init__(self, db: Session):
        self.db = db
        self.gh_client = GitHubClient()
        self.explorer_agent = RepositoryExplorerAgent()
        self.understanding_agent = ProjectUnderstandingAgent()
        self.architecture_agent = TechnologyArchitectureAgent()
        self.matching_agent = SIHMatchingAgent()
        self.problem_analyst_agent = ProblemStatementAnalystAgent()
        self.gap_agent = GapAnalysisAgent()
        self.solution_architect_agent = SolutionArchitectAgent()
        self.planner_agent = ImplementationPlannerAgent()
        self.prompt_agent = PromptGeneratorAgent()
        self.pivot_agent = PivotAdvisorAgent()

    def run_repository_analysis(self, repo: Repository, job: Optional[AnalysisJob] = None) -> RepositoryAnalysis:
        """Executes full repository understanding & top SIH problem matching."""
        logger.info(f"Starting Multi-Agent Analysis for repository: {repo.github_url}")

        self._update_job(job, 15, "Fetching repository metadata & file tree...")
        
        # 1. Freshness Guarantee: Purge stale file records for this repository
        self.db.query(RepositoryFile).filter(RepositoryFile.repository_id == repo.id).delete()
        self.db.commit()

        # 2. Fetch fresh metadata and file tree
        repo_info = self.gh_client.fetch_repository_info(repo.owner, repo.repo_name)
        file_tree = self.gh_client.fetch_file_tree(repo.owner, repo.repo_name, repo_info.get("default_branch", "main"))

        repo.description = repo_info.get("description")
        repo.stars = repo_info.get("stars", 0)
        repo.forks = repo_info.get("forks", 0)
        repo.primary_language = repo_info.get("primary_language", "Unknown")
        self.db.commit()

        # 3. Select priority source files to fetch content (up to 30 files)
        self._update_job(job, 30, "Extracting and sanitizing key project source files...")
        priority_files = [f for f in file_tree if f.get("is_priority")][:30]
        file_contents = {}

        for f in priority_files:
            content = self.gh_client.fetch_file_content(repo.owner, repo.repo_name, f["path"], repo.default_branch)
            if content:
                file_contents[f["path"]] = content
                
                # Save fresh file reference
                rf = RepositoryFile(
                    repository_id=repo.id,
                    path=f["path"],
                    language=f.get("extension", ""),
                    size=f.get("size", 0),
                    content=content[:5000]
                )
                self.db.add(rf)

        self.db.commit()

        # 4. Run Static AST & Framework Analyzer
        self._update_job(job, 45, "Running AST code inspection & architecture analysis...")
        static_analysis = RepositoryStaticAnalyzer.analyze_repository(repo_info, file_tree, file_contents)

        # Create Fresh Analysis Record & Bind to Job
        analysis = RepositoryAnalysis(
            repository_id=repo.id,
            project_type=static_analysis.get("project_type"),
            detected_languages=static_analysis.get("languages"),
            frontend_framework=static_analysis.get("frontend_framework"),
            backend_framework=static_analysis.get("backend_framework"),
            database_tech=static_analysis.get("database_tech"),
            ml_capabilities=static_analysis.get("ml_capabilities"),
            api_routes=static_analysis.get("api_routes"),
            detected_features=static_analysis.get("detected_features"),
        )
        self.db.add(analysis)
        self.db.commit()

        if job:
            job.analysis_id = analysis.id
            self.db.commit()

        context = {
            "db": self.db,
            "repo_info": repo_info,
            "file_tree": file_tree,
            "file_contents": file_contents,
            "static_analysis": static_analysis
        }

        # 5. Agent 1: Repository Explorer
        self._update_job(job, 55, "Agent 1: Exploring repository structure and AST findings...")
        explorer_res = self.explorer_agent.execute_with_tracking(context, self.db, analysis.id)
        context["explorer_findings"] = explorer_res

        # 6. Agent 2: Project Understanding (Builds Capability Manifest)
        self._update_job(job, 65, "Agent 2: Synthesizing grounded Capability Manifest...")
        understanding_res = self.understanding_agent.execute_with_tracking(context, self.db, analysis.id)
        
        manifest = understanding_res.get("capability_manifest", {})
        analysis.project_summary = understanding_res.get("project_summary")
        analysis.target_domains = understanding_res.get("target_domains")
        analysis.grounded_capabilities = understanding_res.get("grounded_capabilities", [])
        analysis.is_low_confidence = understanding_res.get("is_low_confidence", False)
        analysis.confidence_warning = understanding_res.get("confidence_warning")
        self.db.commit()

        # 7. Agent 3: Technology & Architecture
        self._update_job(job, 75, "Agent 3: Evaluating architectural components...")
        arch_res = self.architecture_agent.execute_with_tracking(context, self.db, analysis.id)
        analysis.architectural_strengths = arch_res.get("architectural_strengths")
        analysis.limitations = arch_res.get("limitations")
        self.db.commit()

        # 8. Agent 4: SIH Matching & pgvector Reranker against Capability Manifest
        self._update_job(job, 85, "Agent 4: Matching against SIH 2026 problem statements...")
        grounded_feature_names = [c["capability"] for c in understanding_res.get("grounded_capabilities", [])] if understanding_res.get("grounded_capabilities") else analysis.detected_features
        
        match_context = {
            "db": self.db,
            "repo_info": repo_info,
            "analysis_data": {
                "project_summary": analysis.project_summary,
                "project_type": analysis.project_type,
                "detected_languages": analysis.detected_languages,
                "core_features": grounded_feature_names,
                "technical_capabilities": understanding_res.get("technical_capabilities", []),
                "target_domains": analysis.target_domains,
                "domain_signals": understanding_res.get("domain_signals", []),
                "backend_framework": analysis.backend_framework,
                "frontend_framework": analysis.frontend_framework,
                "ml_capabilities": analysis.ml_capabilities,
                "capability_manifest": manifest
            }
        }
        matching_res = self.matching_agent.execute_with_tracking(match_context, self.db, analysis.id)
        analysis.embedding = matching_res.get("repo_embedding")

        # Save Matches (Top 3 to 6 matches)
        for m in matching_res.get("top_matches", []):
            match_row = ProblemMatch(
                analysis_id=analysis.id,
                problem_statement_id=m["problem_statement_id"],
                overall_match_score=m["overall_match_score"],
                aim_alignment_score=m.get("aim_alignment_score", 0.0),
                semantic_similarity=m["semantic_similarity"],
                feature_alignment=m["feature_alignment"],
                domain_alignment=m["domain_alignment"],
                tech_capability_score=m["tech_capability_score"],
                solution_alignment_score=m["solution_alignment_score"],
                confidence=m["confidence"],
                match_reasoning=m["match_reasoning"],
                existing_capabilities=m["existing_capabilities"],
                missing_capabilities=m["missing_capabilities"],
                reusable_components=m["reusable_components"]
            )
            self.db.add(match_row)

        repo.analysis_status = "COMPLETED"
        repo.analyzed_at = analysis.created_at
        self._update_job(job, 100, "AI Matching Analysis Complete!", status="COMPLETED")
        self.db.commit()

        logger.info(f"Successfully completed multi-agent analysis for {repo.repo_name}")
        return analysis

    def run_deep_gap_and_roadmap(self, match: ProblemMatch) -> Dict[str, Any]:
        """Runs Agents 5 through 9 for a specific problem match."""
        analysis = match.analysis
        ps = match.problem_statement

        # Reconstitute Capability Manifest from analysis grounded capabilities and static data
        manifest_caps = []
        for gc in (analysis.grounded_capabilities or []):
            manifest_caps.append({
                "name": gc.get("capability"),
                "evidence": [gc.get("source")] if gc.get("source") else ["Codebase"],
                "confidence": gc.get("confidence", 0.95)
            })

        reconstituted_manifest = {
            "capabilities": manifest_caps,
            "domain_signals": analysis.target_domains or [],
            "tech_stack": analysis.detected_languages or []
        }

        context = {
            "db": self.db,
            "problem_statement": ps,
            "analysis_data": {
                "project_type": analysis.project_type,
                "detected_languages": analysis.detected_languages,
                "core_features": analysis.detected_features or [],
                "technical_capabilities": analysis.ml_capabilities or [],
                "backend_framework": analysis.backend_framework,
                "frontend_framework": analysis.frontend_framework,
                "database_tech": analysis.database_tech,
                "ml_capabilities": analysis.ml_capabilities or [],
                "capability_manifest": reconstituted_manifest
            },
            "repo_info": {
                "repo_name": analysis.repository.repo_name,
                "owner": analysis.repository.owner
            }
        }

        # Agent 5: Problem Analyst
        problem_res = self.problem_analyst_agent.execute_with_tracking(context, self.db, analysis.id)
        context["problem_analysis"] = problem_res

        # Agent 6: Gap Analysis
        gap_res = self.gap_agent.execute_with_tracking(context, self.db, analysis.id)
        context["gap_data"] = gap_res

        # Agent 10: Pivot Advisor (Triggered only when 15% <= domain_alignment AND reusability < 80%)
        pivot_res = None
        domain_alignment = getattr(match, "domain_alignment", 0.0) or 0.0
        reusability_score = gap_res.get("reusability_score", 0.0)

        if self.pivot_agent.should_trigger(domain_alignment, reusability_score):
            pivot_context = {
                "capability_manifest": reconstituted_manifest,
                "requirement_matrix": gap_res.get("requirement_matrix", []),
                "problem_statement": {
                    "id": ps.id,
                    "title": ps.title,
                    "organization": ps.organization,
                    "theme": ps.theme,
                    "category": ps.category,
                    "description": ps.description,
                    "expected_solution": ps.expected_solution
                },
                "domain_alignment": domain_alignment,
                "reusability_score": reusability_score,
                "analysis_data": context["analysis_data"],
                "repo_info": context["repo_info"]
            }
            pivot_res = self.pivot_agent.execute_with_tracking(pivot_context, self.db, analysis.id)

        # Agent 7: Solution Architect
        arch_res = self.solution_architect_agent.execute_with_tracking(context, self.db, analysis.id)
        context["arch_data"] = arch_res

        # Agent 8: Implementation Planner
        plan_res = self.planner_agent.execute_with_tracking(context, self.db, analysis.id)
        context["plan_data"] = plan_res

        # Agent 9: Coding Prompt Generator
        prompt_res = self.prompt_agent.execute_with_tracking(context, self.db, analysis.id)

        # Persist Gap Analysis
        gap_record = self.db.query(GapAnalysis).filter(GapAnalysis.match_id == match.id).first()
        if not gap_record:
            gap_record = GapAnalysis(
                match_id=match.id,
                requirement_matrix=gap_res.get("requirement_matrix", []),
                summary_findings=gap_res.get("summary_findings"),
                reusability_score=gap_res.get("reusability_score", 0.0)
            )
            self.db.add(gap_record)
        else:
            gap_record.requirement_matrix = gap_res.get("requirement_matrix", [])
            gap_record.summary_findings = gap_res.get("summary_findings")
            gap_record.reusability_score = gap_res.get("reusability_score", 0.0)

        # Persist Implementation Plan
        plan_record = self.db.query(ImplementationPlan).filter(ImplementationPlan.match_id == match.id).first()
        if not plan_record:
            plan_record = ImplementationPlan(
                match_id=match.id,
                phases=plan_res.get("phases", []),
                architecture_overview=arch_res.get("architecture_overview"),
                estimated_effort=plan_res.get("estimated_effort")
            )
            self.db.add(plan_record)
        else:
            plan_record.phases = plan_res.get("phases", [])
            plan_record.architecture_overview = arch_res.get("architecture_overview")
            plan_record.estimated_effort = plan_res.get("estimated_effort")

        # Persist Prompts
        self.db.query(GeneratedPrompt).filter(GeneratedPrompt.match_id == match.id).delete()
        for p in prompt_res.get("generated_prompts", []):
            prompt_item = GeneratedPrompt(
                match_id=match.id,
                category=p["category"],
                title=p["title"],
                prompt_text=p["prompt_text"],
                target_tools=p.get("target_tools", ["Cursor", "Claude Code", "Antigravity"])
            )
            self.db.add(prompt_item)

        self.db.commit()
        return {
            "gap_analysis": gap_res,
            "pivot_advisor": pivot_res,
            "implementation_plan": plan_res,
            "prompts": prompt_res.get("generated_prompts", [])
        }

    def _update_job(self, job: Optional[AnalysisJob], progress: int, step: str, status: str = "RUNNING"):
        if job:
            job.progress_pct = progress
            job.current_step = step
            job.status = status
            self.db.commit()
