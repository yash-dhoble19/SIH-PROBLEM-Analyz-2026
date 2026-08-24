"""
Comprehensive Test Suite for SIH 2026 Project Intelligence Platform.
Tests Neon PostgreSQL models, GitHub security validation, API endpoints, and Multi-Agent pipeline.
"""

import pytest
from fastapi.testclient import TestClient
from app import app
from platform_core.github.security import GitHubSecurityValidator
from platform_core.ai.embeddings import EmbeddingProvider
from platform_core.database.connection import SessionLocal
from platform_core.database.models import ProblemStatement, Repository, RepositoryAnalysis, ProblemMatch
from platform_core.agents.orchestrator import MultiAgentPipeline

client = TestClient(app)


def test_neon_database_integrity():
    """Verify Neon PostgreSQL has all 226 problem statements with embeddings."""
    db = SessionLocal()
    total = db.query(ProblemStatement).count()
    software = db.query(ProblemStatement).filter(ProblemStatement.category == "Software").count()
    hardware = db.query(ProblemStatement).filter(ProblemStatement.category == "Hardware").count()
    db.close()

    assert total == 226, f"Expected 226 records in Neon DB, found {total}"
    assert software == 172, f"Expected 172 Software records, found {software}"
    assert hardware == 54, f"Expected 54 Hardware records, found {hardware}"


def test_api_stats():
    """Verify /api/stats returns accurate aggregations."""
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_records"] == 226
    assert data["software_count"] == 172
    assert data["hardware_count"] == 54
    assert len(data["top_themes"]) > 0
    assert len(data["top_organizations"]) > 0


def test_api_filters():
    """Verify /api/filters returns unique dropdown options."""
    res = client.get("/api/filters")
    assert res.status_code == 200
    data = res.json()
    assert "Software" in data["categories"]
    assert "Hardware" in data["categories"]
    assert len(data["themes"]) >= 15
    assert len(data["organizations"]) >= 30


def test_api_problems_query_and_pagination():
    """Verify search, category filtering, and pagination on /api/problems."""
    # Test query
    res = client.get("/api/problems?category=Software&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 172
    assert len(data["data"]) == 10
    for item in data["data"]:
        assert item["category"] == "Software"

    # Test search
    res = client.get("/api/problems?q=landslide&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1


def test_api_problem_detail():
    """Verify retrieving single problem detail."""
    res = client.get("/api/problems/SIH26001")
    assert res.status_code == 200
    data = res.json()
    assert data["problem_statement_id"] == "SIH26001"
    assert len(data["title"]) > 5
    assert len(data["description"]) > 10


def test_github_security_validator():
    """Test URL parser and security validator."""
    # Valid
    ok, owner, repo, norm = GitHubSecurityValidator.parse_and_validate_url("https://github.com/fastapi/fastapi")
    assert ok is True
    assert owner == "fastapi"
    assert repo == "fastapi"
    assert norm == "https://github.com/fastapi/fastapi"

    # Valid with .git
    ok, owner, repo, norm = GitHubSecurityValidator.parse_and_validate_url("https://github.com/tiangolo/fastapi.git")
    assert ok is True
    assert repo == "fastapi"

    # Invalid - non github
    ok, _, _, err = GitHubSecurityValidator.parse_and_validate_url("https://gitlab.com/user/repo")
    assert ok is False

    # Invalid - traversal
    ok, _, _, err = GitHubSecurityValidator.parse_and_validate_url("https://github.com/../etc/passwd")
    assert ok is False


def test_secret_sanitizer():
    """Test secret masking in file content."""
    raw = "DATABASE_URL=postgresql://admin:secretPass123@host:5432/db\nAPI_KEY = 'sk-12345678901234567890123456789012'"
    sanitized = GitHubSecurityValidator.sanitize_content(raw)
    assert "secretPass123" not in sanitized
    assert "sk-12345678901234567890123456789012" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


def test_embedding_provider():
    """Test 384-dimensional vector embedding generation and normalization."""
    embedder = EmbeddingProvider()
    vec = embedder.get_embedding("Landslide early warning system with IoT sensors and GIS mapping")
    assert len(vec) == 384
    # Check unit norm
    import math
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-4


def test_home_ui_served():
    """Verify HTML UI is correctly served."""
    res = client.get("/")
    assert res.status_code == 200
    assert "SIH 2026 Intelligence Hub" in res.text
    assert "Analyze Your GitHub Repository" in res.text
