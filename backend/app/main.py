"""FastAPI server for the multi-agent SQL analyst."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import db, llm
from .agents.graph import ask, guess_chart
from .config import settings
from .safety import UnsafeSQLError, validate_sql

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="SQL Analyst Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

EXAMPLES = [
    "What was the total revenue in 2025?",
    "Show monthly revenue for 2025",
    "Which product category made the most profit last year?",
    "Top 5 customers by total spend",
    "Compare revenue by region for 2024 and 2025",
    "What is the return rate for each category?",
    "Which payment method is used most in the South region?",
    "How did average order value change by quarter?",
]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class SQLRequest(BaseModel):
    sql: str = Field(min_length=6, max_length=5000)


@app.get("/api/health")
def health():
    configured = True
    try:
        llm.get_llm()
    except llm.LLMNotConfigured:
        configured = False
    return {"status": "ok", "llm_configured": configured, "provider": settings.LLM_PROVIDER,
            "model": llm.model_name(), "database": settings.DB_PATH.name}


@app.get("/api/schema")
def schema():
    return {"tables": db.schema_info()}


@app.get("/api/examples")
def examples():
    return {"examples": EXAMPLES}


@app.post("/api/ask")
async def ask_question(req: AskRequest):
    try:
        return await run_in_threadpool(ask, req.question.strip())
    except llm.LLMNotConfigured as e:
        raise HTTPException(503, str(e)) from e
    except Exception as e:  # noqa: BLE001 - surface LLM/network errors to the UI
        logging.exception("ask failed")
        raise HTTPException(502, f"The language model call failed: {e}") from e


@app.post("/api/sql")
def run_sql(req: SQLRequest):
    """Run a user-edited query (same safety checks as the agents)."""
    try:
        safe = validate_sql(req.sql, settings.ROW_LIMIT)
        result = db.run_query(safe)
    except UnsafeSQLError as e:
        raise HTTPException(400, f"Blocked by safety check: {e}") from e
    except db.QueryError as e:
        raise HTTPException(400, f"Database error: {e}") from e
    return {**result, "sql": safe, "chart": guess_chart(result)}


# In the Docker image the built React app is copied to backend/static and served from "/",
# so the whole project deploys as one container (e.g. on Render or Hugging Face Spaces).
from pathlib import Path  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

_static = Path(__file__).resolve().parent.parent / "static"
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="web")
