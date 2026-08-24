"""
Database package for Neon PostgreSQL integration.
"""

from platform_core.database.connection import engine, SessionLocal, Base, get_db, init_db
from platform_core.database.models import (
    User,
    Organization,
    Theme,
    ProblemStatement,
    Repository,
    RepositoryFile,
    RepositoryAnalysis,
    ProblemMatch,
    GapAnalysis,
    ImplementationPlan,
    GeneratedPrompt,
    AgentRun,
    AnalysisJob,
    Bookmark
)

__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "init_db",
    "User",
    "Organization",
    "Theme",
    "ProblemStatement",
    "Repository",
    "RepositoryFile",
    "RepositoryAnalysis",
    "ProblemMatch",
    "GapAnalysis",
    "ImplementationPlan",
    "GeneratedPrompt",
    "AgentRun",
    "AnalysisJob",
    "Bookmark"
]
