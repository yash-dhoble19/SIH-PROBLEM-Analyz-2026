"""
Export utilities for saving SIH Problem Statements to CSV and JSON formats.
"""

import json
import logging
from pathlib import Path
from typing import List
import pandas as pd

from scraper.models import ProblemStatement

logger = logging.getLogger("sih_scraper.exporter")


class SIHExporter:
    """
    Exports parsed ProblemStatement models to CSV and JSON files with clean formatting.
    """

    def __init__(
        self,
        csv_path: str = "data/processed/sih_2026_problem_statements.csv",
        json_path: str = "data/processed/sih_2026_problem_statements.json",
    ):
        self.csv_path = Path(csv_path)
        self.json_path = Path(json_path)
        
        # Ensure directories exist
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)

    def export_json(self, items: List[ProblemStatement], target_path: Path = None) -> Path:
        """Export list of ProblemStatements to a structured JSON file."""
        out_path = target_path or self.json_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Serialize list of dicts
        data = [item.model_dump() for item in items]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Exported {len(items)} records to JSON: {out_path}")
        return out_path

    def export_csv(self, items: List[ProblemStatement], target_path: Path = None) -> Path:
        """Export list of ProblemStatements to a CSV file using pandas."""
        out_path = target_path or self.csv_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        records = []
        for item in items:
            d = item.model_dump()
            # Serialize extra_fields dict to JSON string for CSV compatibility
            if isinstance(d.get("extra_fields"), dict):
                d["extra_fields"] = json.dumps(d["extra_fields"], ensure_ascii=False) if d["extra_fields"] else ""
            records.append(d)

        df = pd.DataFrame(records)
        # Write with utf-8-sig for seamless opening in Microsoft Excel on Windows
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        logger.info(f"Exported {len(items)} records to CSV: {out_path}")
        return out_path
