"""
Direct Test Runner for SIH Platform.
"""

import sys
import os
from pathlib import Path

# Add root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from app import app
from platform_core.github.security import GitHubSecurityValidator
from platform_core.ai.embeddings import EmbeddingProvider
from platform_core.database.connection import SessionLocal
from platform_core.database.models import ProblemStatement, Repository, RepositoryAnalysis, ProblemMatch

client = TestClient(app)

tests_passed = 0
tests_failed = 0

def run_test(name, fn):
    global tests_passed, tests_failed
    try:
        fn()
        print(f"[PASS] {name}", flush=True)
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] {name}: {e}", flush=True)
        tests_failed += 1

def test_neon_database_integrity():
    db = SessionLocal()
    total = db.query(ProblemStatement).count()
    software = db.query(ProblemStatement).filter(ProblemStatement.category == "Software").count()
    hardware = db.query(ProblemStatement).filter(ProblemStatement.category == "Hardware").count()
    db.close()
    assert total == 226, f"Expected 226 records, got {total}"
    assert software == 172, f"Expected 172 software, got {software}"
    assert hardware == 54, f"Expected 54 hardware, got {hardware}"

def test_api_stats():
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_records"] == 226
    assert data["software_count"] == 172
    assert data["hardware_count"] == 54

def test_api_filters():
    res = client.get("/api/filters")
    assert res.status_code == 200
    data = res.json()
    assert "Software" in data["categories"]
    assert "Hardware" in data["categories"]

def test_api_problems_query():
    res = client.get("/api/problems?category=Software&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 172
    assert len(data["data"]) == 10

def test_api_problem_detail():
    res = client.get("/api/problems/SIH26001")
    assert res.status_code == 200
    data = res.json()
    assert data["problem_statement_id"] == "SIH26001"

def test_github_security():
    ok, owner, repo, norm = GitHubSecurityValidator.parse_and_validate_url("https://github.com/facebook/react")
    assert ok is True
    assert owner == "facebook"
    assert repo == "react"

    ok, _, _, _ = GitHubSecurityValidator.parse_and_validate_url("https://evil.com/repo")
    assert ok is False

def test_secret_sanitization():
    raw = "MY_KEY='sk-12345678901234567890123456789012'"
    sanitized = GitHubSecurityValidator.sanitize_content(raw)
    assert "sk-123" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized

def test_embeddings():
    embedder = EmbeddingProvider()
    vec = embedder.get_embedding("Disaster management and flood warning sensors")
    assert len(vec) == 384

def test_html_home():
    res = client.get("/")
    assert res.status_code == 200
    assert "SIH 2026 Intelligence Hub" in res.text

def test_visitor_analytics_and_ratings():
    # Test visit log
    res_visit = client.post("/api/analytics/visit", json={"session_id": "test_direct_run", "path": "/"})
    assert res_visit.status_code == 200
    # Test analytics stats
    res_stats = client.get("/api/analytics/stats")
    assert res_stats.status_code == 200
    assert "unique_visitors" in res_stats.json()
    # Test rating submission
    res_rate = client.post("/api/ratings", json={
        "rating": 5,
        "target_type": "platform",
        "target_id": "general",
        "author_name": "Direct Test Runner",
        "category": "Overall Experience",
        "review_text": "Production ready!"
    })
    assert res_rate.status_code == 200
    # Test ratings summary
    res_rate_summary = client.get("/api/ratings/stats")
    assert res_rate_summary.status_code == 200
    assert res_rate_summary.json()["total_reviews"] >= 1

if __name__ == "__main__":
    print("========================================", flush=True)
    print("RUNNING SIH INTELLIGENCE PLATFORM TESTS", flush=True)
    print("========================================", flush=True)
    run_test("Neon Database Integrity (226 records)", test_neon_database_integrity)
    run_test("API /api/stats KPI Metrics", test_api_stats)
    run_test("API /api/filters Dropdown Options", test_api_filters)
    run_test("API /api/problems Search & Pagination", test_api_problems_query)
    run_test("API /api/problems/{id} Detail View", test_api_problem_detail)
    run_test("GitHub URL Validation & SSRF Guard", test_github_security)
    run_test("Secret Token & Key Sanitization", test_secret_sanitization)
    run_test("384-Dim Vector Embeddings", test_embeddings)
    run_test("HTML Dashboard Serving", test_html_home)
    run_test("Visitor Analytics & Rating System", test_visitor_analytics_and_ratings)
    print("========================================", flush=True)
    print(f"RESULTS: {tests_passed} PASSED, {tests_failed} FAILED", flush=True)
    print("========================================", flush=True)
    if tests_failed > 0:
        sys.exit(1)

