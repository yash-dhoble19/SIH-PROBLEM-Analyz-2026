"""
Admin Routes for Scraper triggers and System Monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from platform_core.database.connection import get_db
from platform_core.database.models import ProblemStatement, Repository, RepositoryAnalysis, AgentRun

router = APIRouter(prefix="/api/admin", tags=["Admin & System"])


def _run_scraper_job():
    # Lazy import: scraper uses SQLite + local file I/O that crashes on
    # Vercel's read-only /var/task filesystem. Only import when actually called.
    from scraper.scraper import SIHScraper
    scraper = SIHScraper()
    scraper.run(output_format="all")


@router.post("/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    """Triggers the SIH scraper to check for updates from sih.gov.in."""
    background_tasks.add_task(_run_scraper_job)
    return {"status": "success", "message": "SIH Scraper task queued in background."}


@router.get("/metrics")
def get_system_metrics(db: Session = Depends(get_db)):
    """System health and usage stats."""
    total_problems = db.query(ProblemStatement).count()
    total_repos = db.query(Repository).count()
    total_analyses = db.query(RepositoryAnalysis).count()
    total_agent_runs = db.query(AgentRun).count()

    return {
        "status": "HEALTHY",
        "total_problem_statements": total_problems,
        "total_repositories_analyzed": total_repos,
        "total_analyses_completed": total_analyses,
        "total_agent_runs": total_agent_runs
    }
