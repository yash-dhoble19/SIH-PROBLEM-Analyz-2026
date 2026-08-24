"""
API Routes for SIH 2026 Problem Statements Explorer, Filters, and Statistics.
"""

from typing import Optional, List, Any
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, text

from platform_core.database.connection import get_db
from platform_core.database.models import ProblemStatement, Organization, Theme, Bookmark, Repository, AnalysisJob
from platform_core.github.security import GitHubSecurityValidator
from platform_core.api.schemas import AnalyzeRepoRequest, JobStatusResponse

router = APIRouter(prefix="/api", tags=["Problem Statements"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Computes aggregated KPI metrics from Neon PostgreSQL."""
    total = db.query(ProblemStatement).count()
    software = db.query(ProblemStatement).filter(func.lower(ProblemStatement.category) == "software").count()
    hardware = db.query(ProblemStatement).filter(func.lower(ProblemStatement.category) == "hardware").count()

    has_dataset = db.query(ProblemStatement).filter(
        ProblemStatement.dataset_link.isnot(None),
        func.length(func.trim(ProblemStatement.dataset_link)) > 0
    ).count()

    has_youtube = db.query(ProblemStatement).filter(
        ProblemStatement.youtube_link.isnot(None),
        func.length(func.trim(ProblemStatement.youtube_link)) > 0
    ).count()

    # Top 10 Themes
    top_themes_raw = db.query(ProblemStatement.theme, func.count(ProblemStatement.id)).group_by(ProblemStatement.theme).order_by(desc(func.count(ProblemStatement.id))).limit(10).all()
    top_themes = [{"theme": r[0], "count": r[1]} for r in top_themes_raw]

    # Top 10 Organizations
    top_orgs_raw = db.query(ProblemStatement.organization, func.count(ProblemStatement.id)).group_by(ProblemStatement.organization).order_by(desc(func.count(ProblemStatement.id))).limit(10).all()
    top_orgs = [{"organization": r[0], "count": r[1]} for r in top_orgs_raw]

    # All Themes Distribution
    all_themes_raw = db.query(ProblemStatement.theme, func.count(ProblemStatement.id)).group_by(ProblemStatement.theme).all()
    all_themes = {r[0]: r[1] for r in all_themes_raw}

    # All Orgs Distribution
    all_orgs_raw = db.query(ProblemStatement.organization, func.count(ProblemStatement.id)).group_by(ProblemStatement.organization).all()
    all_orgs = {r[0]: r[1] for r in all_orgs_raw}

    return {
        "total_records": total,
        "software_count": software,
        "hardware_count": hardware,
        "unique_ids": total,
        "with_full_description": total,
        "has_dataset_count": has_dataset,
        "has_youtube_count": has_youtube,
        "top_themes": top_themes,
        "top_organizations": top_orgs,
        "all_themes": all_themes,
        "all_organizations": all_orgs,
    }


@router.get("/filters")
def get_filters(db: Session = Depends(get_db)):
    """Retrieves unique categories, themes, and organizations for dropdowns."""
    categories = [r[0] for r in db.query(ProblemStatement.category).distinct().order_by(ProblemStatement.category).all() if r[0]]
    themes = [r[0] for r in db.query(ProblemStatement.theme).distinct().order_by(ProblemStatement.theme).all() if r[0]]
    orgs = [r[0] for r in db.query(ProblemStatement.organization).distinct().order_by(ProblemStatement.organization).all() if r[0]]

    return {
        "categories": categories,
        "themes": themes,
        "organizations": orgs
    }


@router.get("/problems")
def list_problems(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    theme: Optional[str] = Query(None, description="Filter by theme"),
    organization: Optional[str] = Query(None, description="Filter by organization"),
    has_dataset: Optional[bool] = Query(None),
    has_youtube: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("serial_number"),
    sort_order: Optional[str] = Query("asc"),
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Search and filter problem statements with full-text search and filtering."""
    query = db.query(ProblemStatement)

    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.filter(
            func.lower(ProblemStatement.id).like(term) |
            func.lower(ProblemStatement.title).like(term) |
            func.lower(ProblemStatement.organization).like(term) |
            func.lower(ProblemStatement.theme).like(term) |
            func.lower(ProblemStatement.description).like(term) |
            func.lower(ProblemStatement.expected_solution).like(term)
        )

    if category and category.lower() != "all":
        query = query.filter(func.lower(ProblemStatement.category) == category.strip().lower())

    if theme and theme.lower() != "all":
        query = query.filter(func.lower(ProblemStatement.theme) == theme.strip().lower())

    if organization and organization.lower() != "all":
        query = query.filter(func.lower(ProblemStatement.organization) == organization.strip().lower())

    if has_dataset is True:
        query = query.filter(ProblemStatement.dataset_link.isnot(None), func.length(func.trim(ProblemStatement.dataset_link)) > 0)

    if has_youtube is True:
        query = query.filter(ProblemStatement.youtube_link.isnot(None), func.length(func.trim(ProblemStatement.youtube_link)) > 0)

    total_count = query.count()

    # Sort
    order_func = desc if sort_order.lower() == "desc" else asc
    if sort_by == "id":
        query = query.order_by(order_func(ProblemStatement.id))
    elif sort_by == "title":
        query = query.order_by(order_func(ProblemStatement.title))
    else:
        query = query.order_by(order_func(ProblemStatement.serial_number))

    records = query.offset(offset).limit(limit).all()

    data = []
    for r in records:
        data.append({
            "problem_statement_id": r.id,
            "serial_number": r.serial_number,
            "problem_statement_number": r.problem_statement_number,
            "title": r.title,
            "organization": r.organization,
            "department": r.department,
            "category": r.category,
            "theme": r.theme,
            "submitted_ideas_count": r.submitted_ideas_count,
            "deadline_for_idea_submission": r.deadline_for_idea_submission,
            "background": r.background,
            "description": r.description,
            "expected_solution": r.expected_solution,
            "youtube_link": r.youtube_link,
            "dataset_link": r.dataset_link,
            "contact_info": r.contact_info,
            "source_url": r.source_url,
            "search_text": r.search_text,
            "extra_fields": r.extra_fields or {}
        })

    return {
        "total": total_count,
        "count": len(data),
        "limit": limit,
        "offset": offset,
        "data": data
    }


@router.get("/problems/{problem_id}")
def get_problem_detail(problem_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed content for a specific problem statement."""
    ps = db.query(ProblemStatement).filter(func.lower(ProblemStatement.id) == problem_id.strip().lower()).first()
    if not ps:
        raise HTTPException(status_code=404, detail=f"Problem statement '{problem_id}' not found.")

    return {
        "problem_statement_id": ps.id,
        "serial_number": ps.serial_number,
        "problem_statement_number": ps.problem_statement_number,
        "title": ps.title,
        "organization": ps.organization,
        "department": ps.department,
        "category": ps.category,
        "theme": ps.theme,
        "submitted_ideas_count": ps.submitted_ideas_count,
        "deadline_for_idea_submission": ps.deadline_for_idea_submission,
        "background": ps.background,
        "description": ps.description,
        "expected_solution": ps.expected_solution,
        "youtube_link": ps.youtube_link,
        "dataset_link": ps.dataset_link,
        "contact_info": ps.contact_info,
        "source_url": ps.source_url,
        "search_text": ps.search_text,
        "extra_fields": ps.extra_fields or {}
    }
