"""
SIH 2026 Project Intelligence Platform — Main FastAPI Application.
Powered by Neon PostgreSQL + pgvector + Multi-Agent AI Pipeline.
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from platform_core.config import settings
from platform_core.database.connection import init_db
from platform_core.api.routes_problems import router as problems_router
from platform_core.api.routes_analysis import router as analysis_router
from platform_core.api.routes_admin import router as admin_router
from platform_core.api.routes_feedback import router as feedback_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("sih_platform")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Neon PostgreSQL schema and pgvector extension on application startup."""
    logger.info("Initializing Neon PostgreSQL database and pgvector extension...")
    try:
        init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    yield


app = FastAPI(
    title="SIH 2026 Project Intelligence Platform",
    description="AI-Powered SIH Problem Statement Explorer, Repository Analyzer, Gap Matrix, Ratings, and Coding Prompt Generator",
    version="2.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register API routers
app.include_router(problems_router)
app.include_router(analysis_router)
app.include_router(admin_router)
app.include_router(feedback_router)


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main interactive dashboard HTML."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>SIH Intelligence Platform</h1><p>Dashboard UI is being built...</p>")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment probes."""
    return {"status": "ok", "app": "SIH 2026 Intelligence Platform", "version": "2.1.0"}


if __name__ == "__main__":
    port = settings.PORT
    host = settings.HOST
    print(f"Starting SIH 2026 Intelligence Platform on http://{host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=True)
