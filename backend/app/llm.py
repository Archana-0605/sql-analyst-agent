"""LLM access + small helpers for getting reliable JSON / SQL out of it."""

from __future__ import annotations

import json
import re
from typing import Any, List, Tuple

from .config import settings


class LLMNotConfigured(RuntimeError):
    pass


_llm = None


def get_llm():
    """LangChain chat model for the configured provider (cached)."""
    global _llm
    if _llm is not None:
        return _llm
    if settings.LLM_PROVIDER == "gemini":
        if not settings.GOOGLE_API_KEY:
            raise LLMNotConfigured("Set GOOGLE_API_KEY in backend/.env")
        from langchain_google_genai import ChatGoogleGenerativeAI
        _llm = ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, google_api_key=settings.GOOGLE_API_KEY,
                                      temperature=settings.TEMPERATURE)
    else:
        if not settings.GROQ_API_KEY:
            raise LLMNotConfigured("Set GROQ_API_KEY in backend/.env (free key: https://console.groq.com/keys)")
        from langchain_groq import ChatGroq
        _llm = ChatGroq(model=settings.GROQ_MODEL, api_key=settings.GROQ_API_KEY,
                        temperature=settings.TEMPERATURE, max_retries=2)
    return _llm


def set_llm(llm) -> None:
    """Swap the model (used by tests and the offline demo)."""
    global _llm
    _llm = llm


def model_name() -> str:
    return settings.GEMINI_MODEL if settings.LLM_PROVIDER == "gemini" else settings.GROQ_MODEL


def chat(system: str, user: str) -> Tuple[str, dict]:
    """One LLM call. Returns (text, token usage dict)."""
    from langchain_core.messages import HumanMessage, SystemMessage
    msg = get_llm().invoke([SystemMessage(content=system), HumanMessage(content=user)])
    usage = getattr(msg, "usage_metadata", None) or {}
    return (msg.content if isinstance(msg.content, str) else str(msg.content)).strip(), dict(usage)


def parse_json(text: str) -> Any:
    """Pulls the first JSON object out of an LLM reply (tolerates ```json fences and chatter)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = m.group(1) if m else text
    start, depth = candidate.find("{"), 0
    if start == -1:
        raise ValueError("No JSON object in model output")
    for i in range(start, len(candidate)):
        if candidate[i] == "{":
            depth += 1
        elif candidate[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(candidate[start:i + 1])
    raise ValueError("Unterminated JSON object in model output")


def extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    sql = m.group(1) if m else text
    # Drop any leading explanation before the first SELECT/WITH.
    m2 = re.search(r"\b(with|select)\b", sql, re.I)
    if m2:
        sql = sql[m2.start():]
    return sql.strip().rstrip(";").strip()


def as_list(x) -> List[str]:
    if x is None:
        return []
    return x if isinstance(x, list) else [x]
