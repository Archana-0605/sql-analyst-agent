import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


@pytest.fixture(scope="session", autouse=True)
def demo_db():
    db = BACKEND / "data" / "retail.db"
    if not db.exists():
        sys.path.insert(0, str(BACKEND / "data"))
        import seed
        seed.build(db)
    return db


class FakeLLM:
    """Scripted stand-in for the chat model: picks a reply by which agent is asking."""

    def __init__(self, planner=None, writer=None, fixer=None, analyst=None):
        self.replies = {"Planner": list(planner or []), "SQL Writer": list(writer or []),
                        "SQL Fixer": list(fixer or []), "Analyst": list(analyst or [])}
        self.calls = []

    def invoke(self, messages):
        from langchain_core.messages import AIMessage
        system = messages[0].content
        agent = next(a for a in ("SQL Fixer", "SQL Writer", "Planner", "Analyst") if f"You are the {a}" in system)
        self.calls.append(agent)
        return AIMessage(content=self.replies[agent].pop(0),
                         usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})


@pytest.fixture
def fake_llm():
    from app import llm
    from app.agents import graph

    def make(**kw):
        f = FakeLLM(**kw)
        llm.set_llm(f)
        graph._graph = None
        return f
    yield make
    llm.set_llm(None)
