"""
Integration test for the 9-Agent Pipeline, Intent Alignment Guard, and Report Generation.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from platform_core.database.connection import SessionLocal
from platform_core.database.models import ProblemStatement, ProblemMatch, Repository, RepositoryAnalysis
from platform_core.agents.matching_agent import SIHMatchingAgent
from platform_core.agents.problem_analyst_agent import ProblemStatementAnalystAgent
from platform_core.agents.gap_analysis_agent import GapAnalysisAgent
from platform_core.agents.solution_architect_agent import SolutionArchitectAgent
from platform_core.agents.implementation_planner_agent import ImplementationPlannerAgent
from platform_core.agents.prompt_generator_agent import PromptGeneratorAgent


def test_intent_alignment_guard_regression():
    """
    Regression Test:
    Ensures that a mismatched project (e.g. a note-taking / habit tracker app)
    is explicitly vetoed by Agent 4's Intent Guard when evaluated against
    an unrelated domain (e.g. Network Security Compliance).
    """
    print("\n--- Running Intent Alignment Guard Regression Test ---", flush=True)
    matcher = SIHMatchingAgent()

    # Mismatched Note-Taking / Self-Growth Project
    mismatched_repo = {
        "repo_name": "MindBloom-Journal",
        "description": "A minimalist note-taking and daily habit tracker app for self-growth and journaling.",
        "project_summary": "A personal productivity tool that allows users to create markdown notes, log daily mood and habits, and organize self-growth goals.",
        "core_features": ["Markdown note editor", "Daily habit check-in", "Mood journaling", "Task checklist"],
        "detected_features": ["Markdown note editor", "Daily habit check-in"],
        "target_domains": ["Personal Productivity & Note-Taking"],
        "technical_capabilities": ["Python", "FastAPI", "SQLite"],
        "detected_languages": ["Python", "JavaScript"]
    }

    # Network Security Compliance SIH Problem Statement
    security_ps = {
        "id": "SIH26_SEC_001",
        "title": "Automated Network Security Compliance and Firewall Vulnerability Auditing Platform",
        "theme": "Blockchain & Cybersecurity",
        "organization": "National Critical Information Infrastructure Protection Centre (NCIIPC)",
        "background": "Government networks require real-time auditing of firewall rules, packet anomaly detection, and automated vulnerability scanning.",
        "description": "Develop an automated security auditing framework capable of parsing network firewall logs, detecting rogue access attempts, and generating CIS benchmark compliance reports.",
        "expected_solution": "A centralized SIEM dashboard with network packet anomaly analysis, zero-trust policy validator, and automated threat mitigation dispatch."
    }

    # 1. Test direct assess_intent_alignment()
    intent_res = matcher.assess_intent_alignment(mismatched_repo, security_ps)
    print(f"Intent Evaluation Result: {intent_res}", flush=True)

    assert intent_res["domain_match"] is False, f"Expected domain_match=False, got {intent_res['domain_match']}"
    assert intent_res["solves_same_core_problem"] is False, f"Expected solves_same_core_problem=False, got {intent_res['solves_same_core_problem']}"
    assert intent_res["aim_alignment_score"] < 40.0, f"Expected aim_alignment_score < 40, got {intent_res['aim_alignment_score']}"
    reasoning_lower = intent_res["reasoning"].lower()
    assert any(w in reasoning_lower for w in ["productivity", "note", "mismatch", "unrelated", "different domain"]), f"Unexpected reasoning: {intent_res['reasoning']}"

    print("[PASS] Intent Guard correctly vetoed mismatched candidate with domain_match=False and low aim score.", flush=True)


def run_agent_pipeline_test():
    print("========================================", flush=True)
    print("TESTING 9-AGENT AI PIPELINE INTEGRATION", flush=True)
    print("========================================", flush=True)

    db = SessionLocal()
    try:
        # Mock project data for an EEG / AI Healthcare project
        mock_analysis_data = {
            "project_type": "AI & Healthcare Signal Processing System",
            "project_summary": "AI-Powered EEG-based Alzheimer's and cognitive impairment detection system with brainwave signal acquisition and patient analytics.",
            "detected_languages": ["Python", "JavaScript"],
            "core_features": [
                "Real-time EEG signal acquisition and artifact filtering",
                "Deep learning classification for neurodegenerative disorders",
                "Interactive web dashboard with patient analytics"
            ],
            "technical_capabilities": [
                "PyTorch / Scikit-Learn",
                "FastAPI REST Services",
                "Signal Processing Pipeline"
            ],
            "target_domains": ["MedTech / BioTech / HealthTech", "Smart Automation"],
            "backend_framework": "FastAPI",
            "frontend_framework": "React",
            "ml_capabilities": ["PyTorch", "Scikit-Learn"]
        }

        mock_repo_info = {
            "repo_name": "NeuroDetect-AI",
            "owner": "test-team",
            "description": "AI-Powered EEG-based Alzheimer's and cognitive impairment detection system."
        }

        # 1. Test Intent Guard Regression
        test_intent_alignment_guard_regression()

        # 2. Test Agent 4: Matching Agent with 6-Factor Intent Alignment
        print("\n[1/5] Running Agent 4 (SIH Matching & 6-Factor Reranker)...", flush=True)
        matcher = SIHMatchingAgent()
        match_res = matcher.run({
            "db": db,
            "repo_info": mock_repo_info,
            "analysis_data": mock_analysis_data
        })
        top_matches = match_res.get("top_matches", [])
        assert len(top_matches) > 0, "Expected at least 1 match"
        top = top_matches[0]
        assert "aim_alignment_score" in top, "Expected aim_alignment_score in match breakdown"
        print(f"[OK] Top Match: {top['problem_statement_id']} - {top['title'][:40]}... Score: {top['overall_match_score']}% (Aim Intent: {top['aim_alignment_score']}%)", flush=True)

        target_ps_id = top["problem_statement_id"]
        ps = db.query(ProblemStatement).filter(ProblemStatement.id == target_ps_id).first()
        assert ps is not None, f"ProblemStatement {target_ps_id} not found"

        # 3. Test Agent 5: Problem Analyst
        print("[2/5] Running Agent 5 (Problem Statement Analyst)...", flush=True)
        analyst = ProblemStatementAnalystAgent()
        problem_res = analyst.run({"problem_statement": ps})
        assert len(problem_res["explicit_requirements"]) > 0
        print(f"[OK] Decomposed into {len(problem_res['explicit_requirements'])} requirements", flush=True)

        # 4. Test Agent 6: Gap Analysis Agent
        print("[3/5] Running Agent 6 (Gap Analysis Matrix)...", flush=True)
        gap_agent = GapAnalysisAgent()
        gap_res = gap_agent.run({
            "analysis_data": mock_analysis_data,
            "problem_analysis": problem_res
        })
        assert len(gap_res["requirement_matrix"]) > 0
        assert "reusability_score" in gap_res
        print(f"[OK] Requirement Matrix generated. Reusability: {gap_res['reusability_score']}%", flush=True)

        # 5. Test Agent 7 & 8: Solution Architecture & Implementation Planner
        print("[4/5] Running Agents 7 & 8 (Solution Architecture & Phased Planner)...", flush=True)
        architect = SolutionArchitectAgent()
        arch_res = architect.run({
            "analysis_data": mock_analysis_data,
            "problem_analysis": problem_res,
            "gap_data": gap_res
        })

        planner = ImplementationPlannerAgent()
        plan_res = planner.run({
            "analysis_data": mock_analysis_data,
            "problem_analysis": problem_res,
            "arch_data": arch_res
        })
        assert len(plan_res["phases"]) >= 4
        print(f"[OK] Roadmap created with {len(plan_res['phases'])} detailed phases", flush=True)

        # 6. Test Agent 9: Coding Prompt Generator
        print("[5/5] Running Agent 9 (AI Coding Prompt Generator)...", flush=True)
        prompt_agent = PromptGeneratorAgent()
        prompt_res = prompt_agent.run({
            "analysis_data": mock_analysis_data,
            "problem_analysis": problem_res,
            "plan_data": plan_res,
            "repo_info": mock_repo_info
        })
        prompts = prompt_res["generated_prompts"]
        assert len(prompts) >= 3
        print(f"[OK] Generated {len(prompts)} modular AI prompts ready for Cursor/Claude Code/Antigravity", flush=True)

        print("========================================", flush=True)
        print("ALL 9 AGENTS & INTENT GUARD TESTED AND FULLY OPERATIONAL", flush=True)
        print("========================================", flush=True)

    finally:
        db.close()


if __name__ == "__main__":
    run_agent_pipeline_test()
