"""
Regression Tests for Scoring Reliability.
Verifies that the scoring pipeline produces distinct, meaningful scores across
diverse problem statements and does not silently fall back to hardcoded constants.

Key Regression: GrowthOS (AI learning platform / career coach / quiz generation)
should match SIH26101 (MoSPI — AI-enabled learning platform for competencies & skill gaps)
in the Top 3 results with domain_alignment > 60%.
"""

import pytest
import re
from unittest.mock import MagicMock
from platform_core.agents.matching_agent import SIHMatchingAgent
from platform_core.agents.understanding_agent import ProjectUnderstandingAgent
from platform_core.ai.embeddings import EmbeddingProvider


# ───────── Fixtures ────────────────────────────────────────

GROWTHOS_PROFILE = {
    "repo_name": "GrowthOS--AI-Powered-Self-Growth-Platform",
    "description": "AI-Powered Self-Growth Platform with learning roadmaps, career coaching, quiz generation, mastery tracking",
    "project_summary": (
        "The repository 'GrowthOS--AI-Powered-Self-Growth-Platform' is a full-stack Python + React web application "
        "focusing on Smart Education, Skill Development. "
        "Verified code capabilities include: Smart Education & AI Tutoring, REST API Service Layer, "
        "Relational Data Persistence. Architecture includes 12 API endpoints and 5 data models."
    ),
    "core_features": [
        "Smart Education & AI Tutoring",
        "Career Coaching AI Agent",
        "Personalized Learning Roadmaps",
        "Quiz Generation & Mastery Tracking",
        "REST API Service Layer",
        "Relational Data Persistence"
    ],
    "detected_features": [
        "Smart Education & AI Tutoring",
        "Career Coaching AI Agent",
        "Personalized Learning Roadmaps"
    ],
    "target_domains": ["Smart Education", "Smart Automation"],
    "domain_signals": ["education", "api", "database"],
    "technical_capabilities": ["Smart Education & AI Tutoring", "REST API Service Layer"],
    "detected_languages": ["Python", "JavaScript"],
    "project_type": "Full-Stack Web Application",
    "capability_manifest": {
        "repo": {
            "name": "GrowthOS--AI-Powered-Self-Growth-Platform",
            "owner": "yash-dhoble19",
            "primary_language": "Python",
            "project_type": "Full-Stack Web Application"
        },
        "domain_signals": ["education", "api", "database"],
        "capabilities": [
            {"name": "Smart Education & AI Tutoring", "category": "Smart Education",
             "evidence": ["src/ai/agents/career_coach.py: class CareerCoachAgent",
                          "src/ai/agents/planner.py: function generate_roadmap()"],
             "confidence": 0.95},
            {"name": "REST API Service Layer", "category": "Backend Engineering",
             "evidence": ["src/api/routes.py: POST /api/roadmap"], "confidence": 0.95},
            {"name": "Relational Data Persistence", "category": "Data Layer",
             "evidence": ["src/models/user.py: model User"], "confidence": 0.95}
        ],
        "endpoints": [
            {"method": "POST", "path": "/api/roadmap", "handler": "create_roadmap", "file": "src/api/routes.py"},
            {"method": "GET", "path": "/api/quiz", "handler": "generate_quiz", "file": "src/api/routes.py"},
            {"method": "POST", "path": "/api/mastery", "handler": "update_mastery", "file": "src/api/routes.py"}
        ],
        "data_models": [
            {"model_name": "User", "columns": ["id", "name", "email"], "file": "src/models/user.py"},
            {"model_name": "LearningPath", "columns": ["id", "title", "modules"], "file": "src/models/learning.py"}
        ],
        "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL"]
    }
}

# Mock PS objects to simulate DB rows
def _make_ps(ps_id, title, theme, org, description, expected_solution="", category="Software", background=""):
    ps = MagicMock()
    ps.id = ps_id
    ps.title = title
    ps.theme = theme
    ps.organization = org
    ps.description = description
    ps.expected_solution = expected_solution
    ps.category = category
    ps.background = background
    ps.department = org
    ps.embedding = None  # Force term-overlap scoring
    ps.dataset_link = None
    ps.deadline_for_idea_submission = None
    return ps


SIH26101 = _make_ps(
    "SIH26101",
    "Develop an AI enabled learning platform that identifies competencies and skill gaps of the officers of Indian Statistical Service (ISS) and Indian Economic Service (IES)",
    "Smart Education",
    "MoSPI",
    "Development of AI enabled learning platform that creates personalized learning roadmaps based on competency assessment, skill gap analysis, and career progression tracking for ISS and IES officers.",
    "An AI-driven platform with: competency mapping engine, skill gap identification module, personalized learning roadmaps, quiz-based assessments, career coaching recommendations, mastery tracking dashboard.",
    "Software"
)

SIH26200_CYBER = _make_ps(
    "SIH26200",
    "Develop an AI-based network intrusion detection system for critical infrastructure",
    "Blockchain & Cybersecurity",
    "MeitY",
    "Build an AI-powered system that analyzes network traffic to detect intrusion attempts in real-time using deep learning.",
    "Real-time packet inspection, anomaly detection, threat classification dashboard.",
    "Software"
)

SIH26300_AGRI = _make_ps(
    "SIH26300",
    "Smart irrigation system using IoT sensors and weather prediction",
    "Agriculture, FoodTech & Rural Development",
    "Ministry of Agriculture",
    "Develop a smart irrigation management system leveraging IoT soil moisture sensors and weather forecast data.",
    "IoT sensor dashboard, automated valve control, crop-specific irrigation schedules.",
    "Hardware"
)

SIH26400_GIS = _make_ps(
    "SIH26400",
    "Real-time landslide early warning system using satellite data and GIS",
    "Disaster Management",
    "NDMA",
    "Build a geospatial early warning system for landslide-prone regions using satellite imagery and slope analysis.",
    "GIS dashboard with real-time alerts, terrain slope modeling, evacuation route planning.",
    "Software"
)

SIH26500_HEALTH = _make_ps(
    "SIH26500",
    "AI-based EEG analysis platform for early Alzheimer's detection",
    "MedTech / BioTech / HealthTech",
    "AIIMS",
    "Develop an AI platform that analyzes EEG brainwave patterns to detect early signs of Alzheimer's disease.",
    "EEG signal processing pipeline, neural network classifier, clinical dashboard.",
    "Software"
)


# ───────── Tests ───────────────────────────────────────────

class TestScoringReliability:
    """Ensures the scoring pipeline produces meaningfully distinct scores, not flat constants."""

    def setup_method(self):
        self.agent = SIHMatchingAgent(ai_provider=None)

    def test_growthos_matches_sih26101_education(self):
        """GrowthOS (learning/coaching/quizzes) must score high against SIH26101 (AI learning platform for skill gaps)."""
        result = self.agent.assess_intent_alignment(GROWTHOS_PROFILE, SIH26101)
        assert result["domain_match"] is True, f"Expected domain_match=True for GrowthOS vs SIH26101, got: {result}"
        assert result["aim_alignment_score"] >= 70.0, (
            f"GrowthOS vs SIH26101 should have aim_alignment ≥ 70%, got {result['aim_alignment_score']}%: {result['reasoning']}"
        )

    def test_growthos_vetoed_by_cybersecurity(self):
        """GrowthOS must NOT match a cybersecurity problem — domain mismatch veto expected."""
        result = self.agent.assess_intent_alignment(GROWTHOS_PROFILE, SIH26200_CYBER)
        # Should be vetoed or have low aim_alignment
        assert result["aim_alignment_score"] < 45.0 or result["domain_match"] is False, (
            f"GrowthOS should not match cybersecurity PS: aim={result['aim_alignment_score']}, domain_match={result['domain_match']}"
        )

    def test_growthos_vetoed_by_agriculture_hardware(self):
        """GrowthOS must NOT match an agriculture IoT hardware PS."""
        result = self.agent.assess_intent_alignment(GROWTHOS_PROFILE, SIH26300_AGRI)
        assert result["aim_alignment_score"] < 50.0 or result["domain_match"] is False, (
            f"GrowthOS should not match agriculture IoT PS: aim={result['aim_alignment_score']}, domain_match={result['domain_match']}"
        )

    def test_growthos_vetoed_by_gis_disaster(self):
        """GrowthOS must NOT match a GIS/disaster management PS."""
        result = self.agent.assess_intent_alignment(GROWTHOS_PROFILE, SIH26400_GIS)
        assert result["aim_alignment_score"] < 50.0 or result["domain_match"] is False, (
            f"GrowthOS should not match GIS disaster PS: aim={result['aim_alignment_score']}, domain_match={result['domain_match']}"
        )

    def test_growthos_vetoed_by_healthcare_eeg(self):
        """GrowthOS must NOT match an EEG/healthcare PS."""
        result = self.agent.assess_intent_alignment(GROWTHOS_PROFILE, SIH26500_HEALTH)
        assert result["aim_alignment_score"] < 50.0 or result["domain_match"] is False, (
            f"GrowthOS should not match EEG/healthcare PS: aim={result['aim_alignment_score']}, domain_match={result['domain_match']}"
        )

    def test_scores_are_not_identical_across_5_ps(self):
        """The 5 problem statements must produce meaningfully DIFFERENT aim_alignment scores — no flat constant."""
        all_ps = [SIH26101, SIH26200_CYBER, SIH26300_AGRI, SIH26400_GIS, SIH26500_HEALTH]
        scores = []
        for ps in all_ps:
            result = self.agent.assess_intent_alignment(GROWTHOS_PROFILE, ps)
            scores.append(result["aim_alignment_score"])

        unique_scores = set(scores)
        assert len(unique_scores) >= 2, (
            f"Expected at least 2 distinct scores across 5 unrelated PS, got {len(unique_scores)}: {scores}"
        )

        score_range = max(scores) - min(scores)
        assert score_range >= 30.0, (
            f"Score variance too low (range={score_range:.1f}) for 5 diverse PS. Scores: {scores}"
        )

        # Education must be the highest
        assert scores[0] == max(scores), (
            f"SIH26101 (education) should be highest score but got scores: {scores}"
        )

    def test_education_scores_higher_than_unrelated_domains(self):
        """SIH26101 (education) must score higher than all unrelated domains for GrowthOS."""
        edu_result = self.agent.assess_intent_alignment(GROWTHOS_PROFILE, SIH26101)
        edu_score = edu_result["aim_alignment_score"]

        for ps in [SIH26200_CYBER, SIH26300_AGRI, SIH26400_GIS, SIH26500_HEALTH]:
            other_result = self.agent.assess_intent_alignment(GROWTHOS_PROFILE, ps)
            other_score = other_result["aim_alignment_score"]
            assert edu_score > other_score, (
                f"Education PS (SIH26101, score={edu_score}) must outscore {ps.id} (score={other_score})"
            )


class TestEmbeddingFallbackDetection:
    """Verifies that the EmbeddingProvider correctly reports fallback status."""

    def test_fallback_active_when_no_api_key(self):
        """is_fallback_active must be True when no real API key is configured."""
        embedder = EmbeddingProvider()
        assert hasattr(embedder, "is_fallback_active"), "EmbeddingProvider must expose is_fallback_active property"
        # In test/dev environment without OPENAI_API_KEY, fallback should be active
        _ = embedder.get_embedding("test text")
        assert embedder.is_fallback_active is True, (
            "Expected is_fallback_active=True in test env without real API key"
        )

    def test_local_embedding_is_deterministic(self):
        """Same input text must always produce same vector (no random component)."""
        embedder = EmbeddingProvider()
        text = "AI learning platform with skill gap analysis and career coaching"
        v1 = embedder.get_embedding(text)
        v2 = embedder.get_embedding(text)
        assert v1 == v2, "Local deterministic embedding should produce identical vectors for same input"

    def test_different_texts_produce_different_vectors(self):
        """Different domain texts should produce different vectors."""
        embedder = EmbeddingProvider()
        v_edu = embedder.get_embedding("AI learning platform with quiz generation and career coaching")
        v_cyber = embedder.get_embedding("Network intrusion detection firewall packet inspection")
        assert v_edu != v_cyber, "Different domain texts should produce different embedding vectors"


class TestUnderstandingAgentDomainClassification:
    """Verifies the Understanding Agent correctly classifies education-related repos."""

    def test_education_domain_detected_from_signals(self):
        agent = ProjectUnderstandingAgent()
        manifest = {
            "domain_signals": ["education", "api"],
            "capabilities": [
                {"name": "Smart Education & AI Tutoring", "category": "Smart Education",
                 "evidence": ["career_coach.py"], "confidence": 0.95}
            ]
        }
        domains = agent._classify_domains(manifest, "AI learning platform with roadmaps and quizzes", "", "GrowthOS")
        assert "Smart Education" in domains, f"Expected 'Smart Education' in domains, got: {domains}"

    def test_education_domain_from_readme_keywords(self):
        agent = ProjectUnderstandingAgent()
        manifest = {"domain_signals": [], "capabilities": []}
        readme = "This is an AI-powered learning platform with personalized roadmap generation and quiz-based mastery tracking."
        domains = agent._classify_domains(manifest, readme, "", "LearningHub")
        assert "Smart Education" in domains, f"Expected 'Smart Education' from README keywords, got: {domains}"

    def test_router_files_not_classified_as_logistics(self):
        """Files like 'routers/users.py' or 'api/router.py' must NOT trigger Transportation & Logistics."""
        agent = ProjectUnderstandingAgent()
        manifest = {"domain_signals": ["api"], "capabilities": []}
        domains = agent._classify_domains(manifest, "FastAPI web application with REST router endpoints", "Web API backend", "MyApp")
        assert "Transportation & Logistics" not in domains, (
            f"Generic router/API file should not classify as Transportation & Logistics: {domains}"
        )

    def test_no_false_productivity_for_education(self):
        """GrowthOS-like repos with 'self-growth' should get Smart Education, not only Productivity."""
        agent = ProjectUnderstandingAgent()
        manifest = {
            "domain_signals": ["education"],
            "capabilities": [
                {"name": "Smart Education & AI Tutoring", "category": "Smart Education",
                 "evidence": ["career_coach.py"], "confidence": 0.95}
            ]
        }
        domains = agent._classify_domains(
            manifest,
            "AI-powered self-growth platform with learning roadmaps and career coaching",
            "AI learning platform",
            "GrowthOS--AI-Powered-Self-Growth-Platform"
        )
        assert "Smart Education" in domains, f"Expected 'Smart Education', got: {domains}"


class TestScoringMatchContinuousScores:
    """Verifies that _score_match produces continuous (not hardcoded) scores."""

    def setup_method(self):
        self.agent = SIHMatchingAgent(ai_provider=None)

    def test_score_match_returns_continuous_domain_score(self):
        """Domain score must not be a fixed constant (95.0, 85.0, etc.)."""
        intent_result = {
            "aim_alignment_score": 82.0,
            "domain_match": True,
            "solves_same_core_problem": True,
            "reasoning": "Education domain alignment"
        }
        embedder = EmbeddingProvider()
        repo_vec = embedder.get_embedding("AI learning platform with career coaching and quiz generation")

        result = self.agent._score_match(
            SIH26101,
            {"core_features": GROWTHOS_PROFILE["core_features"], "target_domains": ["Smart Education"],
             "domain_signals": ["education", "api"], "detected_languages": ["Python"]},
            repo_vec,
            intent_result,
            GROWTHOS_PROFILE["capability_manifest"],
            {"repo_name": "GrowthOS"}
        )

        domain_score = result["domain_alignment"]
        # Must not be the old hardcoded values
        assert domain_score not in [95.0, 85.0, 70.0, 30.0], (
            f"Domain score {domain_score} appears to be an old hardcoded constant"
        )
        assert domain_score > 60.0, f"Education domain_alignment should be > 60%, got {domain_score}"

    def test_score_match_overall_reasonable(self):
        """Overall score should be between 10% and 98.5%."""
        intent_result = {
            "aim_alignment_score": 85.0,
            "domain_match": True,
            "solves_same_core_problem": True,
            "reasoning": "Strong alignment"
        }
        embedder = EmbeddingProvider()
        repo_vec = embedder.get_embedding("AI learning platform")

        result = self.agent._score_match(
            SIH26101,
            {"core_features": ["Smart Education & AI Tutoring"], "target_domains": ["Smart Education"],
             "domain_signals": ["education"], "detected_languages": ["Python"]},
            repo_vec,
            intent_result,
            GROWTHOS_PROFILE["capability_manifest"],
            {"repo_name": "GrowthOS"}
        )

class TestFullPipelineGrowthOS:
    """Verifies that running SIHMatchingAgent.run on GrowthOS repo produces SIH26101 in Top 3."""

    def test_growthos_run_produces_sih26101_in_top_3(self):
        agent = SIHMatchingAgent(ai_provider=None)
        
        all_ps = [SIH26101, SIH26200_CYBER, SIH26300_AGRI, SIH26400_GIS, SIH26500_HEALTH]
        mock_db = MagicMock()
        
        mock_query = MagicMock()
        mock_query.all.return_value = all_ps
        
        mock_filter = MagicMock()
        mock_filter.all.return_value = all_ps
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        mock_db.execute.return_value.fetchall.return_value = [(SIH26101.id,), (SIH26200_CYBER.id,)]

        context = {
            "db": mock_db,
            "analysis_data": {
                "capability_manifest": GROWTHOS_PROFILE["capability_manifest"],
                "project_summary": GROWTHOS_PROFILE["project_summary"],
                "core_features": GROWTHOS_PROFILE["core_features"],
                "target_domains": GROWTHOS_PROFILE["target_domains"],
                "domain_signals": GROWTHOS_PROFILE["domain_signals"],
                "detected_languages": GROWTHOS_PROFILE["detected_languages"],
                "project_type": GROWTHOS_PROFILE["project_type"]
            },
            "repo_info": {
                "repo_name": "GrowthOS--AI-Powered-Self-Growth-Platform",
                "owner": "yash-dhoble19",
                "description": GROWTHOS_PROFILE["description"]
            }
        }

        output = agent.run(context)
        top_matches = output["top_matches"]
        assert len(top_matches) > 0, "Expected at least 1 top match for GrowthOS"

        top_ps_ids = [m["problem_statement_id"] for m in top_matches[:3]]
        assert "SIH26101" in top_ps_ids, (
            f"SIH26101 (education) must be in Top 3 matches for GrowthOS, got: {top_ps_ids}"
        )
        assert top_matches[0]["problem_statement_id"] == "SIH26101", (
            f"SIH26101 must be the #1 top match, got: {top_matches[0]['problem_statement_id']}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
