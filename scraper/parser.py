"""
HTML and DOM Parser for SIH Problem Statements.
Extracts both list-level row metadata and deep modal details.
"""

import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup, Comment

from scraper.models import ProblemStatement
from scraper.utils import (
    clean_html_to_markdown,
    split_sections,
    extract_valid_url_or_text,
)

logger = logging.getLogger("sih_scraper.parser")


class SIHParser:
    """
    High-fidelity HTML parser for Smart India Hackathon problem statements.
    Extracts table rows and detail modals, preserving complete, un-truncated content.
    """

    def __init__(self, source_url: str = "https://www.sih.gov.in/sih2026PS"):
        self.source_url = source_url

    def parse(self, html_content: str) -> Tuple[List[ProblemStatement], List[str]]:
        """
        Parse complete HTML document and return list of ProblemStatement models
        and a list of any failed row identifiers.
        """
        if not html_content:
            logger.warning("Empty HTML content provided to parser.")
            return [], []

        soup = BeautifulSoup(html_content, "html.parser")
        problem_statements: List[ProblemStatement] = []
        failed_records: List[str] = []

        # Find the main data table
        table = soup.find("table", id="dataTablePS") or soup.find("table")
        if not table:
            logger.error("No problem statement table found in HTML!")
            return [], ["TABLE_NOT_FOUND"]

        tbody = table.find("tbody")
        rows = tbody.find_all("tr", recursive=False) if tbody else table.find_all("tr")[1:]
        
        logger.info(f"Found {len(rows)} problem statement rows in table.")

        for row_idx, row in enumerate(rows):
            tds = row.find_all("td", recursive=False)
            if not tds:
                continue

            # Fallback identifier for logging
            row_id_fallback = f"row_{row_idx + 1}"

            try:
                ps = self._parse_single_row(row, tds, soup, row_idx)
                if ps:
                    problem_statements.append(ps)
                else:
                    failed_records.append(row_id_fallback)
            except Exception as e:
                logger.error(f"Error parsing row {row_idx + 1} ({row_id_fallback}): {e}", exc_info=True)
                failed_records.append(row_id_fallback)

        logger.info(f"Successfully parsed {len(problem_statements)} problem statements. Failed: {len(failed_records)}")
        return problem_statements, failed_records

    def _parse_single_row(
        self,
        row_elem: Any,
        tds: List[Any],
        soup: BeautifulSoup,
        row_idx: int
    ) -> Optional[ProblemStatement]:
        """
        Parse a single row and its corresponding detail modal.
        """
        # Minimum expected columns: S.No., Organization, Title/Modal, Category, PS Number, Ideas, Theme, Deadline
        # Even if column count varies slightly, extract robustly
        s_no_str = tds[0].get_text(strip=True) if len(tds) > 0 else str(row_idx + 1)
        serial_number = int(s_no_str) if s_no_str.isdigit() else (row_idx + 1)

        row_org = tds[1].get_text(strip=True) if len(tds) > 1 else ""
        title_cell = tds[2] if len(tds) > 2 else None
        row_category = tds[3].get_text(strip=True) if len(tds) > 3 else ""
        row_ps_id = tds[4].get_text(strip=True) if len(tds) > 4 else ""
        submitted_ideas = tds[5].get_text(strip=True) if len(tds) > 5 else None
        row_theme = tds[6].get_text(strip=True) if len(tds) > 6 else ""
        deadline = tds[7].get_text(strip=True) if len(tds) > 7 else None

        # Clean title text from cell 2 (cell 2 may contain <a> and modal <div>)
        cell_title = ""
        if title_cell:
            a_tag = title_cell.find("a")
            if a_tag:
                cell_title = a_tag.get_text(strip=True)
            else:
                # If no <a> tag, strip modal div text from cell
                modal_in_cell = title_cell.find(class_=re.compile(r'modal', re.I))
                if modal_in_cell:
                    modal_in_cell.extract()
                cell_title = title_cell.get_text(strip=True)

        # Locate corresponding modal
        # Strategy 1: Look inside the title cell
        modal = title_cell.find(class_=re.compile(r'modal', re.I)) if title_cell else None

        # Strategy 2: Look by ID ViewProblemStatement{num}
        if not modal and row_ps_id:
            numeric_part = re.sub(r'^[A-Za-z]+', '', row_ps_id)
            modal = soup.find(id=f"ViewProblemStatement{numeric_part}") or soup.find(id=f"ViewProblemStatement{row_ps_id}")

        # Strategy 3: Look in <a> data-target attribute
        if not modal and title_cell:
            a_tag = title_cell.find("a")
            if a_tag and a_tag.get("data-target"):
                target_id = a_tag.get("data-target").lstrip("#")
                modal = soup.find(id=target_id)

        modal_data: Dict[str, Any] = {}
        if modal:
            modal_data = self._extract_modal_fields(modal)

        # Determine best field values (prefer detailed modal values, fallback to row table values)
        ps_id = row_ps_id or modal_data.get("problem_statement_id") or f"SIH_{row_idx + 1}"
        ps_num = modal_data.get("problem_statement_number") or re.sub(r'^[A-Za-z]+', '', ps_id)
        
        # Ensure standard SIH format if prefix missing in table
        if not ps_id.startswith("SIH") and ps_id.isdigit():
            ps_id = f"SIH{ps_id}"

        title = modal_data.get("title") or cell_title or "Untitled Problem Statement"
        organization = modal_data.get("organization") or row_org or "Unknown Organization"
        department = modal_data.get("department") or None
        category = modal_data.get("category") or row_category or "Software"
        theme = modal_data.get("theme") or row_theme or "General"
        
        raw_description = modal_data.get("description_raw") or ""
        cleaned_description = clean_html_to_markdown(raw_description) if raw_description else (title_cell.get_text(strip=True) if title_cell else "")

        # Split description into Background, Description, Expected Solution
        bg, desc, sol = split_sections(cleaned_description)

        # Links and Contact
        youtube_link = modal_data.get("youtube_link")
        dataset_link = modal_data.get("dataset_link")
        contact_info = modal_data.get("contact_info")

        return ProblemStatement(
            serial_number=serial_number,
            problem_statement_id=ps_id,
            problem_statement_number=ps_num,
            title=title,
            organization=organization,
            department=department,
            category=category,
            theme=theme,
            submitted_ideas_count=submitted_ideas,
            deadline_for_idea_submission=deadline,
            background=bg,
            description=desc,
            expected_solution=sol,
            youtube_link=youtube_link,
            dataset_link=dataset_link,
            contact_info=contact_info,
            source_url=self.source_url,
            scraping_status="SUCCESS",
            extra_fields=modal_data.get("extra_fields", {})
        )

    def _extract_modal_fields(self, modal_elem: Any) -> Dict[str, Any]:
        """
        Extract key-value pairs and links from modal table rows.
        """
        fields: Dict[str, Any] = {"extra_fields": {}}
        
        modal_table = modal_elem.find("table")
        if not modal_table:
            return fields

        for tr in modal_table.find_all("tr"):
            th_td = tr.find_all(["th", "td"])
            if len(th_td) < 2:
                continue

            raw_key = th_td[0].get_text(strip=True)
            val_td = th_td[1]
            key_norm = raw_key.lower().replace(" ", "_").replace(".", "")

            # Extract full HTML content for Description cell
            if "description" in key_norm:
                # Look for inner div.style-2 or div
                inner_div = val_td.find("div")
                if inner_div:
                    fields["description_raw"] = inner_div.decode_contents()
                else:
                    fields["description_raw"] = val_td.decode_contents()

            elif "problem_statement_id" in key_norm:
                fields["problem_statement_number"] = val_td.get_text(strip=True)

            elif "problem_statement_title" in key_norm or "title" in key_norm:
                fields["title"] = val_td.get_text(strip=True)

            elif "organization" in key_norm:
                fields["organization"] = val_td.get_text(strip=True)

            elif "department" in key_norm:
                # Clean PHP comment remnants if any
                dept_text = val_td.get_text(strip=True)
                dept_text = re.sub(r'<!--.*?-->', '', dept_text).strip()
                fields["department"] = dept_text if dept_text else None

            elif "category" in key_norm:
                fields["category"] = val_td.get_text(strip=True)

            elif "theme" in key_norm:
                fields["theme"] = val_td.get_text(strip=True)

            elif "youtube" in key_norm:
                fields["youtube_link"] = extract_valid_url_or_text(val_td)

            elif "dataset" in key_norm:
                fields["dataset_link"] = extract_valid_url_or_text(val_td)

            elif "contact" in key_norm:
                fields["contact_info"] = extract_valid_url_or_text(val_td)

            else:
                # Store any other dynamically discovered fields
                fields["extra_fields"][raw_key] = extract_valid_url_or_text(val_td) or val_td.get_text(strip=True)

        return fields
