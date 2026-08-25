"""
Application Configuration and Environment Settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import field_validator

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://neondb_owner:npg_Rh7bpJr8mFDg@ep-tiny-bird-ay8cwg72-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
    
    # AI & Embeddings Configuration
    AI_PROVIDER: str = "auto"  # auto, anthropic, openai, gemini, heuristic
    EMBEDDING_PROVIDER: str = "auto"  # auto/local, openai, google
    LOCAL_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    LOCAL_EMBEDDING_DEVICE: str = "cpu"
    GOOGLE_EMBEDDING_MODEL: str = "gemini-embedding-001"
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None
    
    # Server configuration
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    DEBUG: bool = True
    
    # Scraping Defaults
    SIH_SOURCE_URL: str = "https://www.sih.gov.in/sih2026PS"
    SIH_DB_PATH: str = str(BASE_DIR / "data" / "sih_2026.db")

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        """Accept deployment labels injected by common hosting environments."""
        if isinstance(value, str) and value.lower() in {"release", "production", "prod"}:
            return False
        if isinstance(value, str) and value.lower() in {"development", "dev"}:
            return True
        return value

settings = Settings()
