"""
Tests for Visitor Analytics Counter and Project/Platform Rating System.
"""

import pytest
from fastapi.testclient import TestClient
from app import app
from platform_core.database.connection import SessionLocal
from platform_core.database.models import VisitorLog, ProjectRating

client = TestClient(app)


def test_log_visitor_and_increment():
    """Test that posting to /api/analytics/visit registers a unique session."""
    session_id = "test_sess_12345"
    response = client.post("/api/analytics/visit", json={
        "session_id": session_id,
        "path": "/test-route",
        "referrer": "https://google.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_page_views"] >= 1
    assert data["unique_visitors"] >= 1


def test_get_analytics_stats():
    """Test retrieving global platform usage stats."""
    response = client.get("/api/analytics/stats")
    assert response.status_code == 200
    data = response.json()
    assert "unique_visitors" in data
    assert "total_page_views" in data
    assert "total_problems" in data
    assert data["total_problems"] >= 226
    assert data["status"] in ["LIVE", "FALLBACK"]


def test_submit_and_retrieve_rating():
    """Test submitting a platform rating and fetching the aggregated score breakdown."""
    rating_payload = {
        "rating": 5,
        "target_type": "platform",
        "target_id": "general",
        "author_name": "Test Reviewer",
        "category": "Overall Experience",
        "review_text": "Phenomenal SIH Project Intelligence Hub!"
    }
    post_res = client.post("/api/ratings", json=rating_payload)
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["status"] == "success"
    assert "rating_id" in post_data

    # Retrieve stats
    get_res = client.get("/api/ratings/stats?target_type=platform&target_id=general")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["total_reviews"] >= 1
    assert get_data["average_rating"] >= 1.0
    assert len(get_data["recent_reviews"]) >= 1
    assert any(r["author_name"] == "Test Reviewer" for r in get_data["recent_reviews"])


def test_submit_problem_statement_rating():
    """Test submitting a specific problem statement rating (e.g., SIH26001)."""
    rating_payload = {
        "rating": 4,
        "target_type": "problem_statement",
        "target_id": "SIH26001",
        "author_name": "SIH Hacker",
        "category": "Matching Accuracy",
        "review_text": "Accurate alignment with our IoT hardware stack."
    }
    post_res = client.post("/api/ratings", json=rating_payload)
    assert post_res.status_code == 200

    # Retrieve for SIH26001
    get_res = client.get("/api/ratings/SIH26001")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["total_reviews"] >= 1
    assert any(r["target_id"] == "SIH26001" for r in get_data["recent_reviews"])
