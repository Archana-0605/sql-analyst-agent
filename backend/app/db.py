"""
Read-only access to the analytics database.

* The SQLite file is opened with `mode=ro`, so no query can change data.
* Every query runs with a time limit (a progress handler aborts long queries).
* `schema_text()` gives the LLM table/column definitions plus a few sample
  values per text column, which makes its SQL far more accurate.
"""

from __future__ import annotations

import sqlite3
import time
from functools import lru_cache
from typing import Any, Dict, List

from .config import settings


class QueryError(Exception):
    """The database rejected or failed to run the query."""


def connect() -> sqlite3.Connection:
    if not settings.DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {settings.DB_PATH}. Run: python data/seed.py")
    con = sqlite3.connect(f"file:{settings.DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def run_query(sql: str, timeout_s: float | None = None) -> Dict[str, Any]:
    timeout_s = timeout_s or settings.QUERY_TIMEOUT_S
    con = connect()
    deadline = time.time() + timeout_s
    con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 10_000)
    start = time.time()
    try:
        cur = con.execute(sql)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e):
            raise QueryError(f"Query took longer than {timeout_s:.0f}s and was stopped") from e
        raise QueryError(str(e)) from e
    except sqlite3.Error as e:
        raise QueryError(str(e)) from e
    finally:
        con.close()
    return {
        "columns": columns,
        "rows": [[r[c] for c in range(len(columns))] for r in rows],
        "row_count": len(rows),
        "elapsed_ms": int((time.time() - start) * 1000),
    }


@lru_cache(maxsize=1)
def schema_info() -> List[Dict[str, Any]]:
    con = connect()
    tables = []
    try:
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for t in names:
            cols = con.execute(f"PRAGMA table_info('{t}')").fetchall()
            fks = {r["from"]: f"{r['table']}.{r['to']}" for r in con.execute(f"PRAGMA foreign_key_list('{t}')")}
            count = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            col_info = []
            for c in cols:
                info = {"name": c["name"], "type": c["type"], "pk": bool(c["pk"]), "fk": fks.get(c["name"])}
                if c["type"].upper() == "TEXT" and not c["name"].endswith("_date"):
                    distinct = con.execute(f'SELECT COUNT(DISTINCT "{c["name"]}") FROM "{t}"').fetchone()[0]
                    if distinct <= 12:
                        info["values"] = [r[0] for r in con.execute(
                            f'SELECT DISTINCT "{c["name"]}" FROM "{t}" ORDER BY 1')]
                    else:
                        info["examples"] = [r[0] for r in con.execute(
                            f'SELECT DISTINCT "{c["name"]}" FROM "{t}" LIMIT 3')]
                elif c["name"].endswith("_date"):
                    lo, hi = con.execute(f'SELECT MIN("{c["name"]}"), MAX("{c["name"]}") FROM "{t}"').fetchone()
                    info["range"] = [lo, hi]
                col_info.append(info)
            tables.append({"name": t, "row_count": count, "columns": col_info})
    finally:
        con.close()
    return tables


def schema_text() -> str:
    """Compact schema description for prompts."""
    lines = []
    for t in schema_info():
        lines.append(f"TABLE {t['name']} ({t['row_count']} rows)")
        for c in t["columns"]:
            extra = []
            if c["pk"]:
                extra.append("primary key")
            if c["fk"]:
                extra.append(f"-> {c['fk']}")
            if "values" in c:
                extra.append("values: " + ", ".join(map(str, c["values"])))
            elif "examples" in c:
                extra.append("e.g. " + ", ".join(map(str, c["examples"])))
            if "range" in c:
                extra.append(f"from {c['range'][0]} to {c['range'][1]}")
            lines.append(f"  - {c['name']} {c['type']}" + (f"  [{'; '.join(extra)}]" if extra else ""))
    return "\n".join(lines)
