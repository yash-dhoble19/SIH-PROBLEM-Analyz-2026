"""
Unit tests for Scraper Orchestrator and Exporters.
"""

from pathlib import Path
import pytest
from scraper.scraper import SIHScraper


def test_scraper_end_to_end_with_cached_raw(tmp_path):
    fixture_path = Path(__file__).parent / "fixtures" / "sample_problem_statements.html"
    db_path = tmp_path / "sih_test.db"
    csv_path = tmp_path / "sih_test.csv"
    json_path = tmp_path / "sih_test.json"

    scraper = SIHScraper(
        source_url="https://www.sih.gov.in/sih2026PS",
        db_path=str(db_path),
        csv_path=str(csv_path),
        json_path=str(json_path),
        raw_html_path=str(fixture_path),
    )

    statements, summary = scraper.run(output_format="all", save_raw_html=False, use_cached_raw=True)

    assert len(statements) == 2
    assert summary.total_records == 2
    assert summary.software_count == 1
    assert summary.hardware_count == 1
    assert db_path.exists()
    assert csv_path.exists()
    assert json_path.exists()
