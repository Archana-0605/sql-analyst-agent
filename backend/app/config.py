"""Settings, read from environment variables / backend/.env."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


class Settings:
    # LLM: "groq" (default, free tier at console.groq.com) or "gemini"
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

    # Database (any SQLAlchemy-style SQLite path; the demo DB is built by data/seed.py)
    DB_PATH = Path(os.getenv("DB_PATH", BACKEND_DIR / "data" / "retail.db")).resolve()

    # Agent behaviour
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))       # SQL fix attempts after a failure
    ROW_LIMIT = int(os.getenv("ROW_LIMIT", "200"))         # max rows returned to the user
    QUERY_TIMEOUT_S = float(os.getenv("QUERY_TIMEOUT_S", "5"))
    ROWS_FOR_ANALYST = int(os.getenv("ROWS_FOR_ANALYST", "30"))

    CORS_ORIGINS = [o.strip() for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]


settings = Settings()
