"""
The multi-agent analyst, built as a LangGraph state machine.

    START -> planner --(not answerable)--> END
                |
                v
            sql_writer -> executor --(ok)--> analyst -> END
                             ^    |
                             |    +--(error, tries left)--> fixer
                             +------------------------------+
                                  (error, no tries left) --> analyst (explains the failure)

Every node appends to `trace`, which the UI shows as the agents' step-by-step work.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .. import db, llm
from ..config import settings
from ..safety import UnsafeSQLError, validate_sql
from . import prompts


class AnalystState(TypedDict, total=False):
    question: str
    plan: Dict[str, Any]
    sql: str
    attempts: int                 # how many times the executor has run a query
    error: Optional[str]
    result: Optional[Dict[str, Any]]
    answer: str
    chart: Dict[str, Any]
    status: str                   # answered | refused | failed
    trace: List[Dict[str, Any]]
    tokens: int


def _step(state: AnalystState, agent: str, status: str, detail: str, started: float, **extra) -> List[Dict]:
    entry = {"agent": agent, "status": status, "detail": detail,
             "ms": int((time.time() - started) * 1000), **extra}
    return state.get("trace", []) + [entry]


def _tokens(state: AnalystState, usage: dict) -> int:
    return state.get("tokens", 0) + int(usage.get("total_tokens", 0) or 0)


# ------------------------------------------------------------------ nodes
def planner(state: AnalystState) -> AnalystState:
    t0 = time.time()
    text, usage = llm.chat(prompts.PLANNER_SYSTEM.format(schema=db.schema_text()),
                           f"Question: {state['question']}")
    try:
        plan = llm.parse_json(text)
    except (ValueError, TypeError):
        # A malformed plan shouldn't stop the run; the writer can work from the question alone.
        plan = {"answerable": True, "tables": [], "steps": text[:400]}
    answerable = bool(plan.get("answerable", True))
    update: AnalystState = {"plan": plan, "tokens": _tokens(state, usage), "attempts": 0}
    if not answerable:
        reason = plan.get("reason") or "I can only answer questions about this store's sales data."
        update.update(status="refused", answer=reason, chart={"type": "none"},
                      trace=_step(state, "Planner", "refused", reason, t0))
    else:
        tables = ", ".join(llm.as_list(plan.get("tables"))) or "-"
        update["trace"] = _step(state, "Planner", "ok", plan.get("steps", ""), t0, tables=tables)
    return update


def sql_writer(state: AnalystState) -> AnalystState:
    t0 = time.time()
    plan = state.get("plan", {})
    user = (f"Question: {state['question']}\n\nPlan: {plan.get('steps', '')}\n"
            f"Tables: {', '.join(llm.as_list(plan.get('tables')))}")
    text, usage = llm.chat(prompts.WRITER_SYSTEM.format(schema=db.schema_text()), user)
    sql = llm.extract_sql(text)
    return {"sql": sql, "error": None, "tokens": _tokens(state, usage),
            "trace": _step(state, "SQL Writer", "ok", "Wrote a query", t0, sql=sql)}


def executor(state: AnalystState) -> AnalystState:
    t0 = time.time()
    attempts = state.get("attempts", 0) + 1
    try:
        safe_sql = validate_sql(state["sql"], settings.ROW_LIMIT)
        result = db.run_query(safe_sql)
    except UnsafeSQLError as e:
        msg = f"Blocked by safety check: {e}"
        return {"attempts": attempts, "error": msg, "result": None,
                "trace": _step(state, "Executor", "blocked", msg, t0)}
    except db.QueryError as e:
        msg = f"Database error: {e}"
        return {"attempts": attempts, "error": msg, "result": None,
                "trace": _step(state, "Executor", "error", msg, t0)}
    detail = f"Returned {result['row_count']} row{'s' if result['row_count'] != 1 else ''} in {result['elapsed_ms']} ms"
    return {"attempts": attempts, "error": None, "result": result, "sql": safe_sql,
            "trace": _step(state, "Executor", "ok", detail, t0)}


def fixer(state: AnalystState) -> AnalystState:
    t0 = time.time()
    user = (f"Question: {state['question']}\n\nFailed SQL:\n```sql\n{state['sql']}\n```\n\n"
            f"Error: {state['error']}")
    text, usage = llm.chat(prompts.FIXER_SYSTEM.format(schema=db.schema_text()), user)
    sql = llm.extract_sql(text)
    return {"sql": sql, "tokens": _tokens(state, usage),
            "trace": _step(state, "SQL Fixer", "ok", f"Rewrote the query (attempt {state['attempts'] + 1})", t0,
                           sql=sql)}


def analyst(state: AnalystState) -> AnalystState:
    t0 = time.time()
    result = state.get("result")
    if result is None:
        msg = ("I couldn't get a working query for that question after "
               f"{state.get('attempts', 0)} attempts. Last error: {state.get('error')}. "
               "Try rephrasing it, or ask about orders, revenue, products, customers or regions.")
        return {"status": "failed", "answer": msg, "chart": {"type": "none"},
                "trace": _step(state, "Analyst", "failed", "No result to analyse", t0)}

    if result["row_count"] == 0:
        return {"status": "answered", "answer": "The query ran correctly but found no matching data.",
                "chart": {"type": "none"},
                "trace": _step(state, "Analyst", "ok", "Empty result", t0)}

    preview = result["rows"][: settings.ROWS_FOR_ANALYST]
    table = "\n".join([" | ".join(result["columns"])] + [" | ".join(map(str, r)) for r in preview])
    more = f"\n(... {result['row_count'] - len(preview)} more rows)" if result["row_count"] > len(preview) else ""
    user = f"Question: {state['question']}\n\nSQL:\n{state['sql']}\n\nResult:\n{table}{more}"
    text, usage = llm.chat(prompts.ANALYST_SYSTEM, user)
    try:
        out = llm.parse_json(text)
        answer = str(out.get("answer", "")).strip() or text
        chart = sanitize_chart(out.get("chart"), result)
    except (ValueError, TypeError):
        answer, chart = text, guess_chart(result)
    return {"status": "answered", "answer": answer, "chart": chart, "tokens": _tokens(state, usage),
            "trace": _step(state, "Analyst", "ok", "Summarised the result", t0)}


# ------------------------------------------------------------- chart helpers
def _numeric_columns(result: Dict[str, Any]) -> List[str]:
    cols = []
    for i, c in enumerate(result["columns"]):
        vals = [r[i] for r in result["rows"] if r[i] is not None]
        if vals and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
            cols.append(c)
    return cols


def guess_chart(result: Dict[str, Any]) -> Dict[str, Any]:
    cols, nums = result["columns"], _numeric_columns(result)
    if result["row_count"] < 2 or not nums or len(cols) < 2:
        return {"type": "none"}
    x = next((c for c in cols if c not in nums), cols[0])
    y = [c for c in nums if c != x][:2]
    if not y:
        return {"type": "none"}
    timelike = any(k in x.lower() for k in ("month", "date", "year", "quarter", "week", "day"))
    return {"type": "line" if timelike else "bar", "x": x, "y": y, "title": ""}


def sanitize_chart(chart: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    """Keeps the LLM's chart choice only if it refers to real columns; otherwise falls back."""
    if not isinstance(chart, dict) or chart.get("type") not in {"bar", "line", "pie", "none"}:
        return guess_chart(result)
    if chart["type"] == "none":
        return {"type": "none"}
    cols, nums = result["columns"], set(_numeric_columns(result))
    x = chart.get("x")
    y = [c for c in llm.as_list(chart.get("y")) if c in nums and c != x][:2]
    if x not in cols or not y or result["row_count"] < 2:
        return guess_chart(result)
    if chart["type"] == "pie" and (result["row_count"] > 8 or len(y) > 1):
        chart["type"] = "bar"
    return {"type": chart["type"], "x": x, "y": y, "title": str(chart.get("title", ""))[:80]}


# ----------------------------------------------------------------- routing
def after_planner(state: AnalystState) -> str:
    return "end" if state.get("status") == "refused" else "write"


def after_executor(state: AnalystState) -> str:
    if not state.get("error"):
        return "analyse"
    # attempts counts executions; the first run plus MAX_RETRIES fixes.
    return "fix" if state.get("attempts", 0) <= settings.MAX_RETRIES else "analyse"


def build_graph():
    g = StateGraph(AnalystState)
    g.add_node("planner", planner)
    g.add_node("sql_writer", sql_writer)
    g.add_node("executor", executor)
    g.add_node("fixer", fixer)
    g.add_node("analyst", analyst)
    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", after_planner, {"write": "sql_writer", "end": END})
    g.add_edge("sql_writer", "executor")
    g.add_conditional_edges("executor", after_executor, {"analyse": "analyst", "fix": "fixer"})
    g.add_edge("fixer", "executor")
    g.add_edge("analyst", END)
    return g.compile()


_graph = None


def ask(question: str) -> Dict[str, Any]:
    global _graph
    if _graph is None:
        _graph = build_graph()
    t0 = time.time()
    final = _graph.invoke({"question": question, "trace": [], "tokens": 0, "attempts": 0})
    result = final.get("result") or {}
    return {
        "question": question,
        "status": final.get("status", "failed"),
        "answer": final.get("answer", ""),
        "sql": final.get("sql"),
        "columns": result.get("columns", []),
        "rows": result.get("rows", []),
        "row_count": result.get("row_count", 0),
        "chart": final.get("chart", {"type": "none"}),
        "attempts": final.get("attempts", 0),
        "trace": final.get("trace", []),
        "tokens": final.get("tokens", 0),
        "latency_ms": int((time.time() - t0) * 1000),
        "model": llm.model_name(),
    }
