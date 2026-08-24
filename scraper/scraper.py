"""
Main Scraper Orchestrator for SIH 2026 Problem Statements.
"""

import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from scraper.models import ProblemStatement, ScrapeSummary
from scraper.client import SIHWebClient
from scraper.parser import SIHParser
from scraper.database import SIHDatabase
from scraper.exporter import SIHExporter
from scraper.utils import setup_logger

logger = logging.getLogger("sih_scraper")


class SIHScraper:
    """
    Production-grade scraper for Smart India Hackathon problem statements.
    Orchestrates fetching, parsing, validation, database persistence, and exports.
    """

    def __init__(
        self,
        source_url: str = "https://www.sih.gov.in/sih2026PS",
        db_path: str = "data/sih_2026.db",
        csv_path: str = "data/processed/sih_2026_problem_statements.csv",
        json_path: str = "data/processed/sih_2026_problem_statements.json",
        raw_html_path: Optional[str] = "data/raw/sih2026PS_raw.html",
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        self.source_url = source_url
        self.db_path = Path(db_path)
        self.csv_path = Path(csv_path)
        self.json_path = Path(json_path)
        self.raw_html_path = Path(raw_html_path) if raw_html_path else None
        
        self.client = SIHWebClient(timeout=timeout, verify_ssl=verify_ssl)
        self.parser = SIHParser(source_url=source_url)
        self.database = SIHDatabase(db_path=str(self.db_path))
        self.exporter = SIHExporter(csv_path=str(self.csv_path), json_path=str(self.json_path))

    def run(
        self,
        output_format: str = "all",
        save_raw_html: bool = True,
        use_cached_raw: bool = False
    ) -> Tuple[List[ProblemStatement], ScrapeSummary]:
        """
        Executes the scraping pipeline:
        1. Fetch or load HTML
        2. Parse table & modal details
        3. Upsert into SQLite
        4. Export to requested formats (csv, json, database, all)
        5. Generate validation report
        """
        logger.info("========================================")
        logger.info("Starting SIH 2026 Scraper Pipeline")
        logger.info(f"Target URL: {self.source_url}")
        logger.info("========================================")

        html_content = ""

        # Check cached raw HTML option
        if use_cached_raw and self.raw_html_path and self.raw_html_path.exists():
            logger.info(f"Loading cached raw HTML from: {self.raw_html_path}")
            with open(self.raw_html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        else:
            logger.info(f"[INFO] Fetching source page from {self.source_url}")
            html_content = self.client.fetch_html(self.source_url)
            
            # Save raw HTML snapshot if requested
            if save_raw_html and self.raw_html_path:
                self.raw_html_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.raw_html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Saved raw HTML snapshot to: {self.raw_html_path}")

        logger.info("[INFO] Parsing problem statements and details modals...")
        problem_statements, failed_records = self.parser.parse(html_content)
        logger.info(f"[INFO] Found {len(problem_statements)} problem statements.")

        # Persist to database
        if output_format in ("database", "all", "csv", "json"):
            logger.info(f"[INFO] Saving records to database ({self.db_path})...")
            self.database.upsert_many(problem_statements)

        # Export CSV
        if output_format in ("csv", "all"):
            logger.info(f"[INFO] Saving CSV to ({self.csv_path})...")
            self.exporter.export_csv(problem_statements)

        # Export JSON
        if output_format in ("json", "all"):
            logger.info(f"[INFO] Saving JSON to ({self.json_path})...")
            self.exporter.export_json(problem_statements)

        # Compute summary
        summary = self.database.get_summary()
        summary.failed_records = failed_records

        # Print final validation report
        self._print_report(summary)
        return problem_statements, summary

    def _print_report(self, summary: ScrapeSummary):
        """Prints formatted completion report."""
        report = f"""
========================================
SIH 2026 SCRAPING COMPLETE
Total records: {summary.total_records}
Software: {summary.software_count}
Hardware: {summary.hardware_count}
Unique IDs: {summary.unique_ids}
Records with full description: {summary.with_full_description}
Records missing description: {summary.missing_description}
Database: {self.db_path}
CSV: {self.csv_path}
JSON: {self.json_path}
========================================
"""
        print(report)
        if summary.failed_records:
            print("Failed records:")
            for f in summary.failed_records:
                print(f"  - {f}")
        logger.info("[SUCCESS] Scraping completed.")
