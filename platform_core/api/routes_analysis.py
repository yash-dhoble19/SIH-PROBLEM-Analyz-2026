"""
API Routes for GitHub Repository Analysis, Multi-Agent Matching, Gap Matrix, and AI Prompts.
"""

import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session

from platform_core.database.connection import get_db, SessionLocal
from platform_core.database.models import (
    Repository,
    RepositoryAnalysis,
    ProblemMatch,
    GapAnalysis,
    ImplementationPlan,
    GeneratedPrompt,
    AgentRun,
    AnalysisJob,
    ProblemStatement
)
from platform_core.github.security import GitHubSecurityValidator
from platform_core.agents.orchestrator import MultiAgentPipeline
from platform_core.api.schemas import (
    AnalyzeRepoRequest,
    JobStatusResponse,
    AnalysisOverviewResponse,
    ProblemMatchResponse,
    GapAnalysisResponse,
    ImplementationPlanResponse,
    PromptsResponse
)

router = APIRouter(prefix="/api", tags=["Repository Intelligence & Matching"])


def _run_background_analysis(job_id: str, repo_id: str):
    """Background worker task executing multi-agent repository analysis pipeline."""
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        repo = db.query(Repository).filter(Repository.id == uuid.UUID(repo_id)).first()
        if not job or not repo:
            return

        pipeline = MultiAgentPipeline(db)
        pipeline.run_repository_analysis(repo, job)
    except Exception as e:
        if job:
            job.status = "FAILED"
            job.error = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/repositories/analyze", response_model=JobStatusResponse)
def start_repository_analysis(
    req: AnalyzeRepoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Submits a public GitHub URL for static analysis and SIH problem matching."""
    is_valid, owner, repo_name, norm_url = GitHubSecurityValidator.parse_and_validate_url(req.github_url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=norm_url)

    # Check or create Repository
    repo = db.query(Repository).filter(Repository.github_url == norm_url).first()
    if not repo:
        repo = Repository(
            github_url=norm_url,
            owner=owner,
            repo_name=repo_name,
            analysis_status="PENDING"
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = AnalysisJob(
        job_id=job_id,
        repository_id=repo.id,
        target_problem_id=req.target_problem_id,
        status="RUNNING",
        progress_pct=5,
        current_step="Validating repository access and structure..."
    )
    db.add(job)
    db.commit()

    # Dispatch to background tasks
    background_tasks.add_task(_run_background_analysis, job_id, str(repo.id))

    return JobStatusResponse(
        job_id=job_id,
        status="RUNNING",
        progress_pct=5,
        current_step="Analysis job queued successfully."
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Poll the real-time progress of a repository analysis job."""
    job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    analysis_id = None
    if job.status == "COMPLETED":
        if job.analysis_id:
            analysis_id = str(job.analysis_id)
        else:
            latest_analysis = db.query(RepositoryAnalysis).filter(RepositoryAnalysis.repository_id == job.repository_id).order_by(RepositoryAnalysis.created_at.desc()).first()
            if latest_analysis:
                analysis_id = str(latest_analysis.id)

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress_pct=job.progress_pct,
        current_step=job.current_step,
        analysis_id=analysis_id,
        error=job.error
    )


@router.get("/analyses/{analysis_id}")
def get_analysis_overview(analysis_id: str, db: Session = Depends(get_db)):
    """Returns detected repository architecture, capabilities, and ranked SIH matches."""
    try:
        a_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format.")

    analysis = db.query(RepositoryAnalysis).filter(RepositoryAnalysis.id == a_uuid).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    matches = db.query(ProblemMatch).filter(ProblemMatch.analysis_id == analysis.id).order_by(ProblemMatch.overall_match_score.desc()).all()

    matches_data = []
    for m in matches:
        ps = m.problem_statement
        matches_data.append({
            "id": str(m.id),
            "problem_statement_id": m.problem_statement_id,
            "title": ps.title if ps else m.problem_statement_id,
            "category": ps.category if ps else "Software",
            "theme": ps.theme if ps else "General",
            "organization": ps.organization if ps else "Unknown",
            "overall_match_score": m.overall_match_score,
            "aim_alignment_score": getattr(m, "aim_alignment_score", 0.0) or 0.0,
            "semantic_similarity": m.semantic_similarity,
            "feature_alignment": m.feature_alignment,
            "domain_alignment": m.domain_alignment,
            "tech_capability_score": m.tech_capability_score,
            "solution_alignment_score": m.solution_alignment_score,
            "confidence": m.confidence,
            "match_reasoning": m.match_reasoning,
            "existing_capabilities": m.existing_capabilities or [],
            "missing_capabilities": m.missing_capabilities or [],
            "reusable_components": m.reusable_components or [],
            "domain_mismatch_warning": getattr(m, "domain_mismatch_warning", False) or False
        })

    repo = analysis.repository
    return {
        "analysis_id": str(analysis.id),
        "repository_url": repo.github_url,
        "owner": repo.owner,
        "repo_name": repo.repo_name,
        "project_type": analysis.project_type,
        "detected_languages": analysis.detected_languages or [],
        "frontend_framework": analysis.frontend_framework,
        "backend_framework": analysis.backend_framework,
        "database_tech": analysis.database_tech,
        "ml_capabilities": analysis.ml_capabilities or [],
        "detected_features": analysis.detected_features or [],
        "grounded_capabilities": getattr(analysis, "grounded_capabilities", []) or [],
        "target_domains": analysis.target_domains or [],
        "domain_signals": getattr(analysis, "target_domains", []) or [],
        "architectural_strengths": analysis.architectural_strengths or [],
        "limitations": analysis.limitations or [],
        "project_summary": analysis.project_summary,
        "is_low_confidence": getattr(analysis, "is_low_confidence", False) or False,
        "confidence_warning": getattr(analysis, "confidence_warning", None),
        "matches": matches_data
    }


@router.get("/analyses/{analysis_id}/agents")
def get_agent_runs(analysis_id: str, db: Session = Depends(get_db)):
    """Returns observability log of all specialized agents executed for this analysis."""
    try:
        a_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID.")

    runs = db.query(AgentRun).filter(AgentRun.analysis_id == a_uuid).order_by(AgentRun.started_at.asc()).all()
    return [
        {
            "id": str(r.id),
            "agent_name": r.agent_name,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "input_summary": r.input_summary,
            "output_summary": r.output_summary,
            "error_message": r.error_message
        }
        for r in runs
    ]


@router.get("/matches/{match_id}")
def get_match_detail(match_id: str, db: Session = Depends(get_db)):
    """Retrieves full comparison details, gap analysis, and implementation roadmap for a match."""
    try:
        m_uuid = uuid.UUID(match_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid match ID format.")

    match = db.query(ProblemMatch).filter(ProblemMatch.id == m_uuid).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")

    # Ensure Gap Analysis and Roadmap are computed
    if not match.gap_analysis or not match.implementation_plan:
        pipeline = MultiAgentPipeline(db)
        pipeline.run_deep_gap_and_roadmap(match)
        db.refresh(match)

    ps = match.problem_statement
    analysis = match.analysis
    repo = analysis.repository

    gap = match.gap_analysis
    plan = match.implementation_plan
    prompts = match.prompts

    return {
        "match_id": str(match.id),
        "analysis_id": str(analysis.id),
        "repository": {
            "url": repo.github_url,
            "name": repo.repo_name,
            "owner": repo.owner,
            "languages": analysis.detected_languages or [],
            "project_type": analysis.project_type,
            "backend": analysis.backend_framework,
            "frontend": analysis.frontend_framework,
            "ml_capabilities": analysis.ml_capabilities or []
        },
        "problem_statement": {
            "id": ps.id,
            "title": ps.title,
            "organization": ps.organization,
            "department": ps.department,
            "category": ps.category,
            "theme": ps.theme,
            "background": ps.background,
            "description": ps.description,
            "expected_solution": ps.expected_solution,
            "dataset_link": ps.dataset_link,
            "deadline": ps.deadline_for_idea_submission
        },
        "scores": {
            "overall": match.overall_match_score,
            "aim_alignment": getattr(match, "aim_alignment_score", 0.0) or 0.0,
            "semantic": match.semantic_similarity,
            "feature": match.feature_alignment,
            "domain": match.domain_alignment,
            "tech": match.tech_capability_score,
            "solution": match.solution_alignment_score,
            "confidence": match.confidence,
            "reasoning": match.match_reasoning
        },
        "gap_analysis": {
            "reusability_score": gap.reusability_score if gap else 0.0,
            "summary_findings": gap.summary_findings if gap else "",
            "requirement_matrix": gap.requirement_matrix if gap else []
        },
        "implementation_plan": {
            "architecture_overview": plan.architecture_overview if plan else "",
            "estimated_effort": plan.estimated_effort if plan else "",
            "phases": plan.phases if plan else []
        },
        "prompts": [
            {
                "id": str(p.id),
                "category": p.category,
                "title": p.title,
                "prompt_text": p.prompt_text,
                "target_tools": p.target_tools or []
            }
            for p in prompts
        ]
    }


@router.get("/reports/{match_id}/export")
def export_intelligence_report(match_id: str, format: str = "markdown", db: Session = Depends(get_db)):
    """Exports full SIH Project Gap Analysis and Roadmap in Markdown or JSON format."""
    try:
        m_uuid = uuid.UUID(match_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid match ID format.")

    match = db.query(ProblemMatch).filter(ProblemMatch.id == m_uuid).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")

    if not match.gap_analysis or not match.implementation_plan:
        pipeline = MultiAgentPipeline(db)
        pipeline.run_deep_gap_and_roadmap(match)
        db.refresh(match)

    ps = match.problem_statement
    analysis = match.analysis
    repo = analysis.repository
    gap = match.gap_analysis
    plan = match.implementation_plan
    prompts = match.prompts

    if format.lower() == "json":
        data = {
            "match_id": str(match.id),
            "project_name": repo.repo_name,
            "github_url": repo.github_url,
            "sih_problem_id": ps.id,
            "sih_problem_title": ps.title,
            "overall_match_score": match.overall_match_score,
            "gap_matrix": gap.requirement_matrix if gap else [],
            "implementation_phases": plan.phases if plan else [],
            "generated_prompts": [{"title": p.title, "category": p.category, "prompt": p.prompt_text} for p in prompts]
        }
        return data

    # Generate Structured Markdown
    md_content = f"""# SIH 2026 PROJECT INTELLIGENCE REPORT
**Generated by SIH Intelligence Hub**
**Target Problem Statement:** {ps.id} — {ps.title}
**Submitting Ministry/Org:** {ps.organization} | **Category:** {ps.category} | **Theme:** {ps.theme}

---

## 1. PROJECT OVERVIEW
- **Repository:** [{repo.github_url}]({repo.github_url})
- **Project Type:** {analysis.project_type}
- **Detected Stack:** {', '.join(analysis.detected_languages or [])} ({analysis.backend_framework or 'API'} + {analysis.frontend_framework or 'UI'})
- **Overall Match Score:** **{match.overall_match_score}%** (Confidence: {match.confidence})
- **Why It Matches:** {match.match_reasoning}

---

## 2. REQUIREMENT GAP MATRIX
| Requirement | SIH Expectation | Your Project | Status | Reason |
| :--- | :--- | :--- | :--- | :--- |
"""
    if gap and gap.requirement_matrix:
        for r in gap.requirement_matrix:
            md_content += f"| {r['requirement']} | {r['sih_expects']} | {r['current_project']} | **{r['status']}** | {r['reason']} |\n"

    md_content += f"""
---

## 3. IMPLEMENTATION ROADMAP & ARCHITECTURE
**Estimated Effort:** {plan.estimated_effort if plan else '2-3 days'}
**Architecture Strategy:** {plan.architecture_overview if plan else ''}

"""
    if plan and plan.phases:
        for phase in plan.phases:
            md_content += f"""### {phase.get('title', 'Phase')}
- **Why:** {phase.get('why', '')}
- **Existing:** {phase.get('existing_status', '')}
- **Required Changes:** {phase.get('required_changes', '')}
- **Files to Modify:** `{', '.join(phase.get('files_to_modify', []))}`
- **Files to Create:** `{', '.join(phase.get('files_to_create', []))}`
- **Testing:** {phase.get('testing', '')}

"""

    md_content += """---

## 4. MODULAR AI CODING PROMPTS (Ready for Cursor / Claude Code / Antigravity)
"""
    for p in prompts:
        md_content += f"""
### {p.title} ({p.category})
```markdown
{p.prompt_text}
```
"""

    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=SIH_{ps.id}_{repo.repo_name}_Report.md"}
    )
