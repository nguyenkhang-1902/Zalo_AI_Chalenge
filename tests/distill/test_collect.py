from datetime import date

from reasoning_agent.config import AgentConfig

from distill.collect import collect_verified_trace
from distill.trace_generator import TraceResult

_TC = AgentConfig(model="t", base_url="http://x", api_key="")


def test_returns_on_first_verified_attempt():
    calls = {"n": 0}

    def gen(*a, **k):
        calls["n"] += 1
        val = 0 if calls["n"] == 1 else 73  # sai lần 1, đúng lần 2
        return TraceResult(result={"type": "number", "answer": val}, messages=[{"x": calls["n"]}])

    tr = collect_verified_trace(
        "q", "b", date(2026, 3, 29), None, _TC, "number", 73, [], max_attempts=3, generate_fn=gen
    )
    assert calls["n"] == 2 and tr.result["answer"] == 73


def test_returns_none_when_never_verified():
    def gen(*a, **k):
        return TraceResult(result={"type": "number", "answer": 0}, messages=[])

    assert (
        collect_verified_trace(
            "q", "b", date(2026, 3, 29), None, _TC, "number", 73, [], max_attempts=3, generate_fn=gen
        )
        is None
    )
