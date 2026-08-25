"""
Database connection, session management, and engine initialization for Neon PostgreSQL.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from platform_core.config import settings

# Serverless runtimes (Vercel) must not hold persistent connection pools.
# Use NullPool when running on Vercel so each request opens/closes its own
# connection.  For local development, keep a small traditional pool.
_is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

if _is_serverless:
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        connect_args={"connect_timeout": 10},
        echo=False
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 15},
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
    """Ensure pgvector extension is active and create all schema tables safely."""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    except Exception:
        pass

    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE problem_matches ADD COLUMN IF NOT EXISTS aim_alignment_score FLOAT DEFAULT 0.0;"))
            conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS analysis_id UUID;"))
            conn.execute(text("ALTER TABLE repository_analyses ADD COLUMN IF NOT EXISTS grounded_capabilities JSONB DEFAULT '[]'::jsonb;"))
            conn.execute(text("ALTER TABLE repository_analyses ADD COLUMN IF NOT EXISTS is_low_confidence BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE repository_analyses ADD COLUMN IF NOT EXISTS confidence_warning TEXT;"))
            conn.commit()
    except Exception:
        pass

