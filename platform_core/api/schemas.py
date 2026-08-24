"""
Pydantic API Request & Response Schemas.
"""

import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRepoRequest(BaseModel):
    github_url: str = Field(..., description="Public GitHub repository URL (e.g. https://github.com/owner/repo)")
    target_problem_id: Optional[str] = Field(None, description="Optional target SIH problem ID to analyze against directly")


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_pct: int
    current_step: str
    analysis_id: Optional[str] = None
    error: Optional[str] = None


class ProblemMatchResponse(BaseModel):
    id: str
    problem_statement_id: str
    title: str
    category: str
    theme: str
    organization: str
    overall_match_score: float
    aim_alignment_score: Optional[float] = 0.0
    semantic_similarity: float
    feature_alignment: float
    domain_alignment: float
    tech_capability_score: float
    solution_alignment_score: float
    confidence: str
    match_reasoning: Optional[str] = None
    existing_capabilities: List[str] = []
    missing_capabilities: List[str] = []
    reusable_components: List[str] = []


class GroundedCapabilityItem(BaseModel):
    capability: str
    source: str


class AnalysisOverviewResponse(BaseModel):
    analysis_id: str
    repository_url: str
    owner: str
    repo_name: str
    project_type: Optional[str] = None
    detected_languages: List[str] = []
    frontend_framework: Optional[str] = None
    backend_framework: Optional[str] = None
    database_tech: Optional[str] = None
    ml_capabilities: List[str] = []
    detected_features: List[str] = []
    grounded_capabilities: List[GroundedCapabilityItem] = []
    target_domains: List[str] = []
    architectural_strengths: List[str] = []
    limitations: List[str] = []
    project_summary: Optional[str] = None
    is_low_confidence: Optional[bool] = False
    confidence_warning: Optional[str] = None
    matches: List[ProblemMatchResponse] = []


class RequirementGapItem(BaseModel):
    requirement: str
    sih_expects: str
    current_project: str
    status: str  # 'MATCH', 'PARTIAL', 'MISSING', 'UNKNOWN'
    reason: str


class GapAnalysisResponse(BaseModel):
    match_id: str
    problem_statement_id: str
    problem_title: str
    reusability_score: float
    summary_findings: str
    requirement_matrix: List[RequirementGapItem] = []


class ImplementationPhaseItem(BaseModel):
    phase_number: int
    title: str
    why: str
    existing_status: str
    required_changes: str
    files_to_modify: List[str] = []
    files_to_create: List[str] = []
    complexity: str
    testing: str


class ImplementationPlanResponse(BaseModel):
    match_id: str
    architecture_overview: str
    estimated_effort: str
    phases: List[ImplementationPhaseItem] = []


class GeneratedPromptItem(BaseModel):
    category: str
    title: str
    prompt_text: str
    target_tools: List[str] = []


class PromptsResponse(BaseModel):
    match_id: str
    prompts: List[GeneratedPromptItem] = []
