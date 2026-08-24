"""
Database connection, session management, and engine initialization for Neon PostgreSQL.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from platform_core.config import settings

# Create engine with connection pooling and SSL enabled
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Ensure pgvector extension is active and create all schema tables."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.execute(text("ALTER TABLE problem_matches ADD COLUMN IF NOT EXISTS aim_alignment_score FLOAT DEFAULT 0.0;"))
        conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS analysis_id UUID;"))
        conn.execute(text("ALTER TABLE repository_analyses ADD COLUMN IF NOT EXISTS grounded_capabilities JSONB DEFAULT '[]'::jsonb;"))
        conn.execute(text("ALTER TABLE repository_analyses ADD COLUMN IF NOT EXISTS is_low_confidence BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE repository_analyses ADD COLUMN IF NOT EXISTS confidence_warning TEXT;"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
