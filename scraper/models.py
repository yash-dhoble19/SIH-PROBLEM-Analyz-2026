"""
Data models for SIH 2026 problem statements using Pydantic.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class ProblemStatement(BaseModel):
    """
    Strongly typed representation of a Smart India Hackathon problem statement.
    """
    serial_number: Optional[int] = Field(None, description="Sequential row number from the website list")
    problem_statement_id: str = Field(..., description="Unique alphanumeric identifier, e.g. SIH26001")
    problem_statement_number: Optional[str] = Field(None, description="Numeric ID from detail modal, e.g. 26001")
    title: str = Field(..., description="Full title of the problem statement")
    organization: str = Field(..., description="Name of submitting ministry / organization")
    department: Optional[str] = Field(None, description="Specific department within the organization")
    category: str = Field(..., description="Category, typically Software or Hardware")
    theme: str = Field(..., description="Domain/theme, e.g. Disaster Management, Smart Automation")
    submitted_ideas_count: Optional[str] = Field(None, description="Ideas submitted count, e.g. 0/500")
    deadline_for_idea_submission: Optional[str] = Field(None, description="Submission deadline date")
    
    # Detailed content fields
    background: Optional[str] = Field(None, description="Extracted background section")
    description: str = Field(..., description="Full detailed description of the problem statement")
    expected_solution: Optional[str] = Field(None, description="Extracted expected solution / outcomes")
    
    # Additional links and contacts
    youtube_link: Optional[str] = Field(None, description="YouTube reference or explainer link")
    dataset_link: Optional[str] = Field(None, description="Dataset URL or data reference")
    contact_info: Optional[str] = Field(None, description="Contact info, email, or contact link")
    
    # Metadata & Tracking
    source_url: str = Field("https://www.sih.gov.in/sih2026PS", description="Source URL where data was scraped")
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of extraction"
    )
    scraping_status: str = Field("SUCCESS", description="Extraction status (SUCCESS, PARTIAL, FAILED)")
    
    # Derived AI / RAG search text
    search_text: str = Field("", description="Consolidated clean text for future embedding & semantic search")
    
    # Extra discovered fields
    extra_fields: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Any additional dynamic key-values")

    @field_validator("youtube_link", "dataset_link", "contact_info", mode="before")
    @classmethod
    def clean_links(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s or s.lower() in ("none", "null", "n/a", "na", "#", "about:blank"):
            return None
        return s

    @field_validator("department", "background", "expected_solution", mode="before")
    @classmethod
    def clean_optional_strings(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @model_validator(mode="after")
    def compute_search_text(self) -> "ProblemStatement":
        """
        Build a high-quality unified text representation for AI recommendation & RAG pipelines.
        """
        if not self.search_text:
            parts = [
                f"{self.title}",
                f"Organization: {self.organization}",
                f"Category: {self.category}",
                f"Theme: {self.theme}",
            ]
            if self.department and self.department != self.organization:
                parts.append(f"Department: {self.department}")
            if self.background:
                parts.append(f"Background:\n{self.background}")
            if self.description:
                parts.append(f"Description:\n{self.description}")
            if self.expected_solution:
                parts.append(f"Expected Solution:\n{self.expected_solution}")
            
            self.search_text = "\n\n".join(parts)
        return self


class ScrapeSummary(BaseModel):
    """Summary metrics of a scraping execution."""
    total_records: int = 0
    software_count: int = 0
    hardware_count: int = 0
    unique_ids: int = 0
    with_full_description: int = 0
    missing_description: int = 0
    failed_records: list[str] = Field(default_factory=list)
    themes_distribution: Dict[str, int] = Field(default_factory=dict)
    organizations_distribution: Dict[str, int] = Field(default_factory=dict)
    scraped_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
