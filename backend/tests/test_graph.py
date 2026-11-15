import json

from app.agents.graph import ask

PLAN = json.dumps({"answerable": True, "tables": ["orders"], "steps": "Count orders by channel."})
GOOD_SQL = "```sql\nSELECT channel, COUNT(*) AS orders FROM orders GROUP BY channel ORDER BY orders DESC\n```"
ANALYSIS = json.dumps({"answer": "Mobile App and Website lead.",
                       "chart": {"type": "bar", "x": "channel", "y": ["orders"], "title": "Orders by channel"}})


def test_happy_path(fake_llm):
    f = fake_llm(planner=[PLAN], writer=[GOOD_SQL], analyst=[ANALYSIS])
    out = ask("How many orders per channel?")
    assert out["status"] == "answered"
    assert out["row_count"] == 3 and out["columns"] == ["channel", "orders"]
    assert out["chart"]["type"] == "bar" and out["attempts"] == 1
    assert [s["agent"] for s in out["trace"]] == ["Planner", "SQL Writer", "Executor", "Analyst"]
    assert f.calls == ["Planner", "SQL Writer", "Analyst"] and out["tokens"] == 45


def test_self_correction(fake_llm):
    bad = "```sql\nSELECT channel, COUNT(*) FROM orderz GROUP BY channel\n```"
    f = fake_llm(planner=[PLAN], writer=[bad], fixer=[GOOD_SQL], analyst=[ANALYSIS])
    out = ask("How many orders per channel?")
    assert out["status"] == "answered" and out["attempts"] == 2
    agents = [s["agent"] for s in out["trace"]]
    assert agents == ["Planner", "SQL Writer", "Executor", "SQL Fixer", "Executor", "Analyst"]
    assert out["trace"][2]["status"] == "error"


def test_blocked_write_then_gives_up(fake_llm):
    drop = "```sql\nDROP TABLE orders\n```"
    f = fake_llm(planner=[PLAN], writer=[drop], fixer=[drop] * 3)
    out = ask("Remove the orders")
    assert out["status"] == "failed" and out["attempts"] == 4   # 1 try + 3 fixes
    assert all(s["status"] == "blocked" for s in out["trace"] if s["agent"] == "Executor")
    assert "Analyst" not in f.calls


def test_refusal(fake_llm):
    f = fake_llm(planner=[json.dumps({"answerable": False, "reason": "I can't change data."})])
    out = ask("Delete all cancelled orders")
    assert out["status"] == "refused" and out["rows"] == [] and f.calls == ["Planner"]


def test_bad_chart_falls_back(fake_llm):
    weird = json.dumps({"answer": "ok", "chart": {"type": "pie", "x": "nope", "y": ["also_nope"]}})
    fake_llm(planner=[PLAN], writer=[GOOD_SQL], analyst=[weird])
    out = ask("Orders per channel")
    assert out["chart"]["type"] == "bar" and out["chart"]["x"] == "channel"
