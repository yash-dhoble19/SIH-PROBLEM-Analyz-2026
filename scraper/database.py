"""
SQLite Database Layer for storing and managing SIH Problem Statements with UPSERT support.
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from scraper.models import ProblemStatement, ScrapeSummary

logger = logging.getLogger("sih_scraper.database")


class SIHDatabase:
    """
    Manages SQLite database storage for SIH problem statements.
    Ensures safe idempotency via SQLite UPSERT syntax and provides summary queries.
    """

    def __init__(self, db_path: str = "data/sih_2026.db"):
        self.db_path = Path(db_path)
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection with Row factory configured."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates the problem_statements table and relevant indexes if they don't exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS problem_statements (
            problem_statement_id TEXT PRIMARY KEY,
            serial_number INTEGER,
            problem_statement_number TEXT,
            title TEXT NOT NULL,
            organization TEXT NOT NULL,
            department TEXT,
            category TEXT NOT NULL,
            theme TEXT NOT NULL,
            submitted_ideas_count TEXT,
            deadline_for_idea_submission TEXT,
            background TEXT,
            description TEXT NOT NULL,
            expected_solution TEXT,
            youtube_link TEXT,
            dataset_link TEXT,
            contact_info TEXT,
            source_url TEXT NOT NULL,
            scraped_at TEXT NOT NULL,
            scraping_status TEXT NOT NULL,
            search_text TEXT NOT NULL,
            extra_fields TEXT
        );
        """
        create_indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_ps_category ON problem_statements(category);
        CREATE INDEX IF NOT EXISTS idx_ps_theme ON problem_statements(theme);
        CREATE INDEX IF NOT EXISTS idx_ps_org ON problem_statements(organization);
        """
        with self._get_connection() as conn:
            conn.executescript(create_table_sql)
            conn.executescript(create_indexes_sql)
            conn.commit()
        logger.debug(f"Database initialized at {self.db_path}")

    def upsert_many(self, problem_statements: List[ProblemStatement]) -> int:
        """
        Inserts or updates multiple problem statements.
        Guarantees no duplicate records on repeated runs.
        """
        if not problem_statements:
            return 0

        upsert_sql = """
        INSERT INTO problem_statements (
            problem_statement_id,
            serial_number,
            problem_statement_number,
            title,
            organization,
            department,
            category,
            theme,
            submitted_ideas_count,
            deadline_for_idea_submission,
            background,
            description,
            expected_solution,
            youtube_link,
            dataset_link,
            contact_info,
            source_url,
            scraped_at,
            scraping_status,
            search_text,
            extra_fields
        ) VALUES (
            :problem_statement_id,
            :serial_number,
            :problem_statement_number,
            :title,
            :organization,
            :department,
            :category,
            :theme,
            :submitted_ideas_count,
            :deadline_for_idea_submission,
            :background,
            :description,
            :expected_solution,
            :youtube_link,
            :dataset_link,
            :contact_info,
            :source_url,
            :scraped_at,
            :scraping_status,
            :search_text,
            :extra_fields
        )
        ON CONFLICT(problem_statement_id) DO UPDATE SET
            serial_number = excluded.serial_number,
            problem_statement_number = excluded.problem_statement_number,
            title = excluded.title,
            organization = excluded.organization,
            department = excluded.department,
            category = excluded.category,
            theme = excluded.theme,
            submitted_ideas_count = excluded.submitted_ideas_count,
            deadline_for_idea_submission = excluded.deadline_for_idea_submission,
            background = excluded.background,
            description = excluded.description,
            expected_solution = excluded.expected_solution,
            youtube_link = excluded.youtube_link,
            dataset_link = excluded.dataset_link,
            contact_info = excluded.contact_info,
            source_url = excluded.source_url,
            scraped_at = excluded.scraped_at,
            scraping_status = excluded.scraping_status,
            search_text = excluded.search_text,
            extra_fields = excluded.extra_fields;
        """

        records = []
        for ps in problem_statements:
            data = ps.model_dump()
            data["extra_fields"] = json.dumps(data.get("extra_fields") or {})
            records.append(data)

        with self._get_connection() as conn:
            conn.executemany(upsert_sql, records)
            conn.commit()

        logger.info(f"Upserted {len(records)} records into {self.db_path}")
        return len(records)

    def get_by_id(self, ps_id: str) -> Optional[ProblemStatement]:
        """Fetch a single problem statement by ID."""
        sql = "SELECT * FROM problem_statements WHERE problem_statement_id = ?;"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (ps_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("extra_fields"):
                    d["extra_fields"] = json.loads(d["extra_fields"])
                return ProblemStatement(**d)
        return None

    def get_all(self) -> List[ProblemStatement]:
        """Fetch all problem statements ordered by serial_number / ID."""
        sql = "SELECT * FROM problem_statements ORDER BY serial_number ASC, problem_statement_id ASC;"
        results = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                d = dict(row)
                if d.get("extra_fields"):
                    d["extra_fields"] = json.loads(d["extra_fields"])
                results.append(ProblemStatement(**d))
        return results

    def get_summary(self) -> ScrapeSummary:
        """Computes validation metrics and categorical distributions from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM problem_statements;")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT problem_statement_id) FROM problem_statements;")
            unique_ids = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM problem_statements WHERE LOWER(category) = 'software';")
            software = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM problem_statements WHERE LOWER(category) = 'hardware';")
            hardware = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM problem_statements WHERE description IS NOT NULL AND length(trim(description)) > 0;")
            with_desc = cursor.fetchone()[0]

            missing_desc = total - with_desc

            # Distribution of Themes
            cursor.execute("SELECT theme, COUNT(*) FROM problem_statements GROUP BY theme ORDER BY COUNT(*) DESC;")
            themes = {row[0]: row[1] for row in cursor.fetchall()}

            # Distribution of Organizations
            cursor.execute("SELECT organization, COUNT(*) FROM problem_statements GROUP BY organization ORDER BY COUNT(*) DESC;")
            orgs = {row[0]: row[1] for row in cursor.fetchall()}

        return ScrapeSummary(
            total_records=total,
            software_count=software,
            hardware_count=hardware,
            unique_ids=unique_ids,
            with_full_description=with_desc,
            missing_description=missing_desc,
            themes_distribution=themes,
            organizations_distribution=orgs,
        )
