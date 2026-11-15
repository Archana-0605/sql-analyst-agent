"""
SQL guardrails. Every query the LLM writes passes through `validate_sql`
before it touches the database. Three layers of defence:

1. Parse with sqlglot: exactly ONE statement, and it must be a SELECT
   (including WITH ... SELECT and UNION of SELECTs).
2. Keyword blocklist as a second check, in case the parser is lenient.
3. The database itself is opened read-only (see db.py), so even a query that
   slipped past 1 and 2 could not modify data.

It also enforces a LIMIT so a "SELECT *" on a big table can't flood the UI.
"""

import re

import sqlglot
from sqlglot import exp

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|vacuum|"
    r"reindex|grant|revoke|merge|exec|execute|load_extension)\b",
    re.IGNORECASE,
)


class UnsafeSQLError(ValueError):
    """The generated SQL is not a single read-only SELECT."""


def strip_code_fences(sql: str) -> str:
    sql = sql.strip()
    m = re.search(r"```(?:sql)?\s*(.*?)```", sql, re.S | re.I)
    if m:
        sql = m.group(1)
    return sql.strip().rstrip(";").strip()


def _without_strings(sql: str) -> str:
    """Blank out string literals so a value like 'Drop Shipping' isn't flagged."""
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def validate_sql(sql: str, row_limit: int) -> str:
    """Returns a safe, LIMITed version of `sql`, or raises UnsafeSQLError."""
    sql = strip_code_fences(sql)
    if not sql:
        raise UnsafeSQLError("Empty query")

    try:
        statements = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except sqlglot.errors.ParseError as e:
        # Let SQLite report real syntax errors (the fixer agent uses that message),
        # but still refuse anything that looks like a write.
        if FORBIDDEN.search(_without_strings(sql)):
            raise UnsafeSQLError("Only read-only SELECT queries are allowed") from e
        return sql
    if len(statements) != 1:
        raise UnsafeSQLError("Only one SQL statement is allowed")

    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise UnsafeSQLError(f"Only SELECT queries are allowed (got {tree.key.upper()})")
    if FORBIDDEN.search(_without_strings(sql)):
        raise UnsafeSQLError("Only read-only SELECT queries are allowed")

    # Enforce a row limit on the outermost query.
    limit = tree.args.get("limit")
    if limit is None:
        sql = f"{sql}\nLIMIT {row_limit}"
    else:
        try:
            n = int(limit.expression.name)
            if n > row_limit:
                sql = re.sub(r"\bLIMIT\s+\d+\s*$", f"LIMIT {row_limit}", sql, flags=re.I)
        except (AttributeError, ValueError):
            pass
    return sql
