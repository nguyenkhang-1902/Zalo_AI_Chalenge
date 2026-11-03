import json
from datetime import date
from decimal import Decimal

from reasoning_agent.react_loop import BUDGET_EXHAUSTED_REASON, ToolSpec, run_react_loop


def test_tool_result_with_decimal_and_date_does_not_crash():
    def handler():
        return {"total": Decimal("12.50"), "day": date(2026, 3, 1)}

    registry = {
        "peek": ToolSpec(
            schema={"name": "peek", "description": "d", "parameters": {"type": "object", "properties": {}, "required": []}},
            handler=handler,
        )
    }
    calls = {"n": 0}

    def chat_fn(messages, tools, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"content": None, "tool_calls": [{"id": "1", "name": "peek", "arguments": "{}"}]}
        return {
            "content": None,
            "tool_calls": [
                {"id": "2", "name": "submit_answer", "arguments": json.dumps({"type": "number", "answer_json": "12.5"})}
            ],
        }

    assert run_react_loop(chat_fn, "sys", "q", registry) == {"type": "number", "answer": 12.5}


def test_budget_exhausted_reason_constant_matches_result():
    def chat_fn(messages, tools, timeout):
        raise RuntimeError("server down")

    result = run_react_loop(chat_fn, "sys", "q", {})
    assert result == {"type": "unanswerable", "reason": BUDGET_EXHAUSTED_REASON}
