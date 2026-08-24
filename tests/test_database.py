"""
Unit tests for SQLite database operations and UPSERT behavior.
"""

import pytest
from scraper.database import SIHDatabase
from scraper.models import ProblemStatement


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_sih.db"
    return SIHDatabase(db_path=str(db_file))


def test_database_upsert_and_duplicates(temp_db):
    ps1 = ProblemStatement(
        serial_number=1,
        problem_statement_id="SIH26001",
        problem_statement_number="26001",
        title="Original Title",
        organization="MDoNER",
        category="Software",
        theme="Disaster Management",
        description="Original description text",
    )

    # Insert first time
    count = temp_db.upsert_many([ps1])
    assert count == 1

    fetched = temp_db.get_by_id("SIH26001")
    assert fetched is not None
    assert fetched.title == "Original Title"

    # Update with same ID
    ps1_updated = ProblemStatement(
        serial_number=1,
        problem_statement_id="SIH26001",
        problem_statement_number="26001",
        title="Updated Title V2",
        organization="MDoNER",
        category="Software",
        theme="Disaster Management",
        description="Updated description text",
    )
    temp_db.upsert_many([ps1_updated])

    # Ensure no duplicate row was created, and title was updated
    all_rows = temp_db.get_all()
    assert len(all_rows) == 1
    assert all_rows[0].title == "Updated Title V2"

    # Verify summary
    summary = temp_db.get_summary()
    assert summary.total_records == 1
    assert summary.unique_ids == 1
    assert summary.software_count == 1
    assert summary.hardware_count == 0
