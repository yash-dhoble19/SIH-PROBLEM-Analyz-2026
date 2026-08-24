"""
Relational Database Models for SIH Intelligence Platform using SQLAlchemy and pgvector.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from platform_core.database.connection import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=True)
    username = Column(String(100), unique=True, index=True, nullable=True)
    role = Column(String(50), default="user")  # 'user', 'admin'
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    code = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    problem_statements = relationship("ProblemStatement", back_populates="organization_rel")


class Theme(Base):
    __tablename__ = "themes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    problem_statements = relationship("ProblemStatement", back_populates="theme_rel")


class ProblemStatement(Base):
    __tablename__ = "problem_statements"

    id = Column(String(50), primary_key=True)  # e.g., 'SIH26001'
    serial_number = Column(Integer, nullable=True, index=True)
    problem_statement_number = Column(String(50), nullable=True)
    title = Column(Text, nullable=False, index=True)
    organization = Column(String(255), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    department = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False, index=True)  # 'Software', 'Hardware'
    theme = Column(String(255), nullable=False, index=True)
    theme_id = Column(UUID(as_uuid=True), ForeignKey("themes.id"), nullable=True)
    submitted_ideas_count = Column(String(50), nullable=True)
    deadline_for_idea_submission = Column(String(100), nullable=True)
    
    # Detailed text
    background = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    expected_solution = Column(Text, nullable=True)
    
    # Links & Contact
    youtube_link = Column(Text, nullable=True)
    dataset_link = Column(Text, nullable=True)
    contact_info = Column(Text, nullable=True)
    
    # Metadata & Tracking
    source_url = Column(Text, default="https://www.sih.gov.in/sih2026PS")
    scraped_at = Column(DateTime(timezone=True), default=utcnow)
    scraping_status = Column(String(50), default="SUCCESS")
    
    # Clean derived text for embeddings and RAG
    search_text = Column(Text, nullable=False)
    
    # Vector embedding (384-dim for MiniLM / standard embeddings)
    embedding = Column(Vector(384), nullable=True)
    
    # Dynamic extra fields
    extra_fields = Column(JSON, default=dict)

    organization_rel = relationship("Organization", back_populates="problem_statements")
    theme_rel = relationship("Theme", back_populates="problem_statements")
    matches = relationship("ProblemMatch", back_populates="problem_statement", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="problem_statement", cascade="all, delete-orphan")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_url = Column(String(500), unique=True, nullable=False, index=True)
    owner = Column(String(100), nullable=False, index=True)
    repo_name = Column(String(100), nullable=False, index=True)
    default_branch = Column(String(50), default="main")
    visibility = Column(String(20), default="public")
    commit_sha = Column(String(100), nullable=True)
    primary_language = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    analysis_status = Column(String(50), default="PENDING")  # 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'

    files = relationship("RepositoryFile", back_populates="repository", cascade="all, delete-orphan")
    analyses = relationship("RepositoryAnalysis", back_populates="repository", cascade="all, delete-orphan")
    jobs = relationship("AnalysisJob", back_populates="repository", cascade="all, delete-orphan")


class RepositoryFile(Base):
    __tablename__ = "repository_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(500), nullable=False)
    language = Column(String(50), nullable=True)
    size = Column(Integer, default=0)
    content_hash = Column(String(64), nullable=True)
    is_relevant = Column(Boolean, default=True)
    content = Column(Text, nullable=True)  # sanitized textual content for key files
    created_at = Column(DateTime(timezone=True), default=utcnow)

    repository = relationship("Repository", back_populates="files")


class RepositoryAnalysis(Base):
    __tablename__ = "repository_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    project_summary = Column(Text, nullable=True)
    project_type = Column(String(100), nullable=True)  # e.g., 'Full-Stack Web App', 'ML Pipeline', 'Embedded/IoT'
    detected_languages = Column(JSON, default=list)
    frontend_framework = Column(String(100), nullable=True)
    backend_framework = Column(String(100), nullable=True)
    database_tech = Column(String(100), nullable=True)
    ml_capabilities = Column(JSON, default=list)
    api_routes = Column(JSON, default=list)
    detected_features = Column(JSON, default=list)
    target_domains = Column(JSON, default=list)
    architectural_strengths = Column(JSON, default=list)
    limitations = Column(JSON, default=list)
    
    # Vector embedding of repository semantic representation
    embedding = Column(Vector(384), nullable=True)
    raw_agent_outputs = Column(JSON, default=dict)
    grounded_capabilities = Column(JSON, default=list)  # List of {capability, source}
    is_low_confidence = Column(Boolean, default=False)
    confidence_warning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    repository = relationship("Repository", back_populates="analyses")
    matches = relationship("ProblemMatch", back_populates="analysis", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="analysis", cascade="all, delete-orphan")


class ProblemMatch(Base):
    __tablename__ = "problem_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("repository_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_statement_id = Column(String(50), ForeignKey("problem_statements.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Match Scoring Breakdown
    overall_match_score = Column(Float, nullable=False)  # 0.0 to 100.0
    aim_alignment_score = Column(Float, default=0.0)  # Intent alignment score (0.0 to 100.0)
    semantic_similarity = Column(Float, default=0.0)
    feature_alignment = Column(Float, default=0.0)
    domain_alignment = Column(Float, default=0.0)
    tech_capability_score = Column(Float, default=0.0)
    solution_alignment_score = Column(Float, default=0.0)
    confidence = Column(String(20), default="High")  # 'High', 'Medium', 'Low'
    
    # Detailed Reasoning
    match_reasoning = Column(Text, nullable=True)
    existing_capabilities = Column(JSON, default=list)
    missing_capabilities = Column(JSON, default=list)
    reusable_components = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    analysis = relationship("RepositoryAnalysis", back_populates="matches")
    problem_statement = relationship("ProblemStatement", back_populates="matches")
    gap_analysis = relationship("GapAnalysis", back_populates="match", uselist=False, cascade="all, delete-orphan")
    implementation_plan = relationship("ImplementationPlan", back_populates="match", uselist=False, cascade="all, delete-orphan")
    prompts = relationship("GeneratedPrompt", back_populates="match", cascade="all, delete-orphan")


class GapAnalysis(Base):
    __tablename__ = "gap_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("problem_matches.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Comparison Matrix: list of {requirement, sih_expects, current_project, status: MATCH|PARTIAL|MISSING|UNKNOWN, reason}
    requirement_matrix = Column(JSON, default=list)
    summary_findings = Column(Text, nullable=True)
    reusability_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    match = relationship("ProblemMatch", back_populates="gap_analysis")


class ImplementationPlan(Base):
    __tablename__ = "implementation_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("problem_matches.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Phased roadmap: list of {phase_number, title, why, existing_status, required_changes, files_to_modify, files_to_create, complexity, testing}
    phases = Column(JSON, default=list)
    architecture_overview = Column(Text, nullable=True)
    estimated_effort = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    match = relationship("ProblemMatch", back_populates="implementation_plan")


class GeneratedPrompt(Base):
    __tablename__ = "generated_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("problem_matches.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # 'Backend', 'Frontend', 'AI/ML', 'Database', 'Deployment', 'Testing'
    title = Column(String(255), nullable=False)
    prompt_text = Column(Text, nullable=False)
    target_tools = Column(JSON, default=lambda: ["Cursor", "Claude Code", "Antigravity", "Gemini"])
    created_at = Column(DateTime(timezone=True), default=utcnow)

    match = relationship("ProblemMatch", back_populates="prompts")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("repository_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(50), default="QUEUED")  # 'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED'
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, default=0)

    analysis = relationship("RepositoryAnalysis", back_populates="agent_runs")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("repository_analyses.id", ondelete="SET NULL"), nullable=True)
    target_problem_id = Column(String(50), nullable=True)  # if analyzing against 1 specific problem
    status = Column(String(50), default="PENDING")  # 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
    progress_pct = Column(Integer, default=0)
    current_step = Column(String(255), default="Initializing analysis job...")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    repository = relationship("Repository", back_populates="jobs")


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(String(100), nullable=True, index=True)
    problem_statement_id = Column(String(50), ForeignKey("problem_statements.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="bookmarks")
    problem_statement = relationship("ProblemStatement", back_populates="bookmarks")
