import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
from run_eval import gold_result, results_match  # noqa: E402

from app.main import app  # noqa: E402


def test_results_match():
    assert results_match([[1, "a"], [2, "b"]], [["b", 2.0], ["a", 1]])          # col + row order ignored
    assert results_match([[100.0]], [[100.04]])                                   # float tolerance
    assert results_match([["x", 5]], [["x", 5, 99]])                               # extra column ok
    assert not results_match([[1], [2]], [[1]])
    assert not results_match([["a", 1], ["b", 2]], [["a", 2], ["b", 1]])         # rows must line up
    assert not results_match([["a"], ["b"]], [["b"], ["a"]], ordered=True)


def test_every_gold_query_runs():
    qs = [json.loads(l) for l in (Path(__file__).resolve().parents[1] / "eval" / "questions.jsonl").read_text().splitlines()]
    for q in qs:
        if q["gold_sql"]:
            assert gold_result(q["gold_sql"]), q["question"]


def test_api(fake_llm):
    c = TestClient(app)
    assert c.get("/api/schema").json()["tables"]
    assert c.get("/api/examples").json()["examples"]
    r = c.post("/api/sql", json={"sql": "SELECT category, COUNT(*) AS n FROM products GROUP BY category"})
    assert r.status_code == 200 and r.json()["row_count"] == 6 and r.json()["chart"]["type"] == "bar"
    assert c.post("/api/sql", json={"sql": "DELETE FROM orders"}).status_code == 400
    fake_llm(planner=[json.dumps({"answerable": False, "reason": "Off topic."})])
    r = c.post("/api/ask", json={"question": "What's the weather?"})
    assert r.status_code == 200 and r.json()["status"] == "refused"
