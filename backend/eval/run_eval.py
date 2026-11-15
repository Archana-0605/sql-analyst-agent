"""
Benchmark the multi-agent analyst.

For each question in eval/questions.jsonl the full agent graph runs exactly as
it does in the app. Metrics written to eval/results/metrics.json:

* execution_accuracy  - share of answerable questions whose result matches the
                        gold query's result (values compared, column names and
                        row order ignored unless order matters, floats with tolerance)
* by_difficulty       - the same split into easy / medium / hard
* first_try_accuracy  - correct without needing the SQL Fixer
* self_corrected      - questions that failed first but were fixed by the Fixer agent
* refusal_accuracy    - unsafe / off-topic questions correctly refused or blocked
* avg_latency_s, avg_tokens

    python eval/run_eval.py                 # all questions
    python eval/run_eval.py --limit 10      # quick check

Results are saved per question as they finish (eval/results/predictions.jsonl),
and a re-run skips questions already done; use --fresh to start over.
Groq's free tier has rate limits, so --sleep pauses between questions.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
RESULTS = EVAL_DIR / "results"


# ------------------------------------------------------------ comparison
def _norm(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return s.lower()


def _eq(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=5e-3, abs_tol=0.051)
    return a == b


def _key(v):
    return (v is None, isinstance(v, str), round(v, 1) if isinstance(v, float) else (v if v is not None else 0))


def _col_match(gold_col, pred_col, ordered: bool) -> bool:
    if len(gold_col) != len(pred_col):
        return False
    if not ordered:
        gold_col, pred_col = sorted(gold_col, key=_key), sorted(pred_col, key=_key)
    return all(_eq(a, b) for a, b in zip(gold_col, pred_col))


def results_match(gold_rows, pred_rows, ordered: bool = False) -> bool:
    """True if the predicted result holds the same values as the gold result.
    Column names are ignored; extra predicted columns are allowed (e.g. a helpful
    count beside the answer); row order only matters when `ordered`."""
    if len(gold_rows) != len(pred_rows):
        return False
    if not gold_rows:
        return True
    g_cols = [[_norm(r[i]) for r in gold_rows] for i in range(len(gold_rows[0]))]
    p_cols = [[_norm(r[i]) for r in pred_rows] for i in range(len(pred_rows[0]))]
    idx, used = [], set()
    for gc in g_cols:
        hit = next((j for j, pc in enumerate(p_cols) if j not in used and _col_match(gc, pc, ordered)), None)
        if hit is None:
            return False
        used.add(hit)
        idx.append(hit)
    if ordered:
        return True
    # Each column matched on its own; now check the rows line up as whole rows.
    rowkey = lambda t: tuple(_key(v) for v in t)  # noqa: E731
    g = sorted((tuple(_norm(v) for v in r) for r in gold_rows), key=rowkey)
    p = sorted((tuple(_norm(r[j]) for j in idx) for r in pred_rows), key=rowkey)
    return all(all(_eq(a, b) for a, b in zip(gr, pr)) for gr, pr in zip(g, p))


def gold_result(sql: str):
    con = sqlite3.connect(f"file:{settings.DB_PATH}?mode=ro", uri=True)
    try:
        return [list(r) for r in con.execute(sql).fetchall()]
    finally:
        con.close()


# ------------------------------------------------------------ run
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=2.0, help="seconds between questions (rate limits)")
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args()

    from app.agents.graph import ask

    questions = [json.loads(l) for l in (EVAL_DIR / "questions.jsonl").read_text().splitlines() if l.strip()]
    if args.limit:
        questions = questions[: args.limit]
    RESULTS.mkdir(exist_ok=True)
    pred_path = RESULTS / "predictions.jsonl"
    if args.fresh and pred_path.exists():
        pred_path.unlink()
    done = {}
    if pred_path.exists():
        for line in pred_path.read_text().splitlines():
            if line.strip():
                p = json.loads(line)
                done[p["id"]] = p

    with open(pred_path, "a", encoding="utf-8") as f:
        for q in questions:
            if q["id"] in done:
                continue
            try:
                out = ask(q["question"])
                err = None
            except Exception as e:  # noqa: BLE001 - record and keep going (e.g. rate limit)
                out, err = {}, str(e)
            rec = {"id": q["id"], "difficulty": q["difficulty"], "question": q["question"],
                   "status": out.get("status", "error"), "sql": out.get("sql"),
                   "attempts": out.get("attempts", 0), "latency_ms": out.get("latency_ms", 0),
                   "tokens": out.get("tokens", 0), "error": err}
            if q["gold_sql"]:
                rec["correct"] = bool(out.get("status") == "answered" and
                                      results_match(gold_result(q["gold_sql"]), out.get("rows", []), q["ordered"]))
            else:
                # Refusal check: the agents must not return data for these.
                rec["correct"] = out.get("status") in ("refused", "failed") or (err is None and not out.get("rows"))
            done[q["id"]] = rec
            f.write(json.dumps(rec) + "\n")
            f.flush()
            mark = "✓" if rec["correct"] else "✗"
            print(f"{mark} [{q['difficulty']:6}] #{q['id']:>2} {q['question'][:70]}  "
                  f"(attempts {rec['attempts']}, {rec['latency_ms'] / 1000:.1f}s){'  ERROR: ' + err if err else ''}",
                  flush=True)
            time.sleep(args.sleep)

    preds = [done[q["id"]] for q in questions if q["id"] in done]
    answerable = [p for p in preds if p["difficulty"] != "refuse"]
    refuse = [p for p in preds if p["difficulty"] == "refuse"]
    pct = lambda xs: round(100 * sum(xs) / len(xs), 1) if xs else None  # noqa: E731
    metrics = {
        "model": settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq" else settings.GEMINI_MODEL,
        "questions": len(preds),
        "execution_accuracy": pct([p["correct"] for p in answerable]),
        "by_difficulty": {d: pct([p["correct"] for p in answerable if p["difficulty"] == d])
                          for d in ("easy", "medium", "hard")},
        "first_try_accuracy": pct([p["correct"] and p["attempts"] == 1 for p in answerable]),
        "self_corrected": sum(1 for p in answerable if p["correct"] and p["attempts"] > 1),
        "refusal_accuracy": pct([p["correct"] for p in refuse]),
        "avg_attempts": round(sum(p["attempts"] for p in answerable) / max(len(answerable), 1), 2),
        "avg_latency_s": round(sum(p["latency_ms"] for p in preds) / max(len(preds), 1) / 1000, 2),
        "avg_tokens": round(sum(p["tokens"] for p in preds) / max(len(preds), 1)),
        "errors": dict(Counter(p["status"] for p in preds)),
    }
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
