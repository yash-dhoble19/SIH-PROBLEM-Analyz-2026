"""
Command Line Interface (CLI) entrypoint for SIH 2026 Problem Statement Scraper.
"""

import argparse
import sys
import os
import logging
from scraper.scraper import SIHScraper
from scraper.utils import setup_logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Production Scraper for Smart India Hackathon (SIH) 2026 Problem Statements."
    )
    parser.add_argument(
        "--output",
        choices=["csv", "json", "database", "all"],
        default="all",
        help="Specify output format (default: all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Equivalent to --output all (exports to SQLite database, CSV, and JSON)",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("SIH_SOURCE_URL", "https://www.sih.gov.in/sih2026PS"),
        help="Source URL to scrape",
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("SIH_DB_PATH", "data/sih_2026.db"),
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--csv-path",
        default=os.getenv("SIH_CSV_PATH", "data/processed/sih_2026_problem_statements.csv"),
        help="Path for CSV output",
    )
    parser.add_argument(
        "--json-path",
        default=os.getenv("SIH_JSON_PATH", "data/processed/sih_2026_problem_statements.json"),
        help="Path for JSON output",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Use previously saved raw HTML snapshot instead of refetching from network",
    )
    parser.add_argument(
        "--no-raw-cache",
        action="store_true",
        help="Do not save raw HTML snapshot to data/raw/",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Configure logging
    log_level = getattr(logging, args.log_level)
    setup_logger("sih_scraper", level=log_level)

    output_mode = "all" if args.all else args.output

    scraper = SIHScraper(
        source_url=args.url,
        db_path=args.db_path,
        csv_path=args.csv_path,
        json_path=args.json_path,
        raw_html_path="data/raw/sih2026PS_raw.html" if not args.no_raw_cache else None,
    )

    try:
        problem_statements, summary = scraper.run(
            output_format=output_mode,
            save_raw_html=not args.no_raw_cache,
            use_cached_raw=args.use_cache,
        )
        if summary.total_records == 0:
            sys.exit(1)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Scraper execution failed: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
