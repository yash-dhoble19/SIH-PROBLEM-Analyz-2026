"""
Unit tests for Pydantic models and search_text generation.
"""

import pytest
from scraper.models import ProblemStatement


def test_problem_statement_model():
    ps = ProblemStatement(
        serial_number=1,
        problem_statement_id="SIH26001",
        problem_statement_number="26001",
        title="AI Flood Warning",
        organization="Ministry of Jal Shakti",
        department="Central Water Commission",
        category="Software",
        theme="Disaster Management",
        background="Floods occur during monsoon.",
        description="Build an AI model for water levels.",
        expected_solution="Real-time warning dashboard.",
        youtube_link="https://youtube.com/watch?v=123",
        dataset_link="https://cwc.gov.in/data",
        contact_info="support@cwc.gov.in",
    )

    assert ps.problem_statement_id == "SIH26001"
    assert ps.category == "Software"
    assert "AI Flood Warning" in ps.search_text
    assert "Organization: Ministry of Jal Shakti" in ps.search_text
    assert "Theme: Disaster Management" in ps.search_text
    assert "Background:\nFloods occur during monsoon." in ps.search_text
    assert "Expected Solution:\nReal-time warning dashboard." in ps.search_text


def test_problem_statement_null_links_cleaning():
    ps = ProblemStatement(
        problem_statement_id="SIH26002",
        title="Hardware Sensor",
        organization="DRDO",
        category="Hardware",
        theme="Robotics",
        description="Sensor unit",
        youtube_link=" NA ",
        dataset_link="None",
        contact_info="#",
    )

    assert ps.youtube_link is None
    assert ps.dataset_link is None
    assert ps.contact_info is None
