"""
Unit tests for SIH Parser.
"""

from pathlib import Path
import pytest
from scraper.parser import SIHParser
from scraper.utils import clean_html_to_markdown, split_sections


@pytest.fixture
def sample_html() -> str:
    fixture_path = Path(__file__).parent / "fixtures" / "sample_problem_statements.html"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()


def test_parse_sample_html(sample_html):
    parser = SIHParser()
    statements, failed = parser.parse(sample_html)

    assert len(failed) == 0
    assert len(statements) == 2

    # Verify Record 1 (Software)
    ps1 = statements[0]
    assert ps1.problem_statement_id == "SIH26001"
    assert ps1.problem_statement_number == "26001"
    assert ps1.category == "Software"
    assert ps1.theme == "Disaster Management"
    assert ps1.organization == "Ministry of Development of North Eastern Region (MDoNER)"
    assert ps1.department == "Disaster Management Cell"
    assert ps1.submitted_ideas_count == "12/500"
    assert ps1.youtube_link == "https://youtube.com/watch?v=sample123"
    assert ps1.dataset_link == "https://data.gov.in/dataset/ner-landslide"
    assert ps1.contact_info == "sih-support@ner.gov.in"
    assert ps1.background is not None
    assert "frequently faces landslides" in ps1.background
    assert ps1.expected_solution is not None
    assert "GIS dashboard" in ps1.expected_solution
    assert "• Feature A: Data collection" in ps1.description

    # Verify Record 2 (Hardware, empty optional links)
    ps2 = statements[1]
    assert ps2.problem_statement_id == "SIH26004"
    assert ps2.category == "Hardware"
    assert ps2.theme == "MedTech / BioTech / HealthTech"
    assert ps2.youtube_link is None
    assert ps2.dataset_link is None
    assert ps2.contact_info is None
    assert "portable hardware kit" in ps2.description


def test_clean_html_to_markdown():
    raw_html = "<p>Line 1</p><br/><b>Bold Title:</b><ul><li>Item 1</li><li>Item 2</li></ul>"
    clean = clean_html_to_markdown(raw_html)
    assert "**Bold Title:**" in clean
    assert "• Item 1" in clean
    assert "• Item 2" in clean
    assert "<p>" not in clean
    assert "<br/>" not in clean


def test_split_sections():
    text = """**Background:**
This is the background story.

**Description:**
Detailed requirements here.
• Req 1
• Req 2

**Expected Solution:**
Final working deliverable.
"""
    bg, desc, sol = split_sections(text)
    assert bg is not None and "background story" in bg
    assert desc is not None and "Detailed requirements" in desc
    assert sol is not None and "Final working deliverable" in sol
