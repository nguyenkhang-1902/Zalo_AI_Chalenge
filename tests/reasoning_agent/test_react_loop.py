import json
import time

from reasoning_agent.react_loop import MAX_TOOL_CALLS, ToolSpec, run_react_loop


def _make_chat_fn(responses):
    calls = []

    def chat_fn(messages, tools, timeout):
        calls.append((messages, tools, timeout))
        return responses[len(calls) - 1]

    return chat_fn, calls


def test_calls_submit_answer_tool_to_finish():
    responses = [
        {
            "content": None,
            "tool_calls": [{"id": "1", "name": "submit_answer", "arguments": '{"type": "number", "answer_json": "42"}'}],
        }
    ]
    chat_fn, calls = _make_chat_fn(responses)

    result = run_react_loop(chat_fn, "system prompt", "câu hỏi?", {})

    assert result == {"type": "number", "answer": 42}
    assert len(calls) == 1


def test_dispatches_tool_call_then_submit_answer_in_next_turn():
    echo_tool = ToolSpec(
        schema={
            "name": "echo",
            "description": "echo",
            "parameters": {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]},
        },
        handler=lambda x: {"doubled": x * 2},
    )
    responses = [
        {"content": None, "tool_calls": [{"id": "1", "name": "echo", "arguments": '{"x": 5}'}]},
        {"content": None, "tool_calls": [{"id": "2", "name": "submit_answer", "arguments": '{"type": "number", "answer_json": "10"}'}]},
    ]
    chat_fn, calls = _make_chat_fn(responses)

    result = run_react_loop(chat_fn, "system prompt", "câu hỏi?", {"echo": echo_tool})

    assert result == {"type": "number", "answer": 10}
    second_call_messages = calls[1][0]
    tool_messages = [m for m in second_call_messages if m.get("role") == "tool"]
    assert json.loads(tool_messages[0]["content"]) == {"doubled": 10}


def test_unknown_tool_name_returns_error_without_raising():
    responses = [
        {"content": None, "tool_calls": [{"id": "1", "name": "khong_ton_tai", "arguments": "{}"}]},
        {"content": None, "tool_calls": [{"id": "2", "name": "submit_answer", "arguments": '{"type": "unanswerable", "reason": "test"}'}]},
    ]
    chat_fn, calls = _make_chat_fn(responses)

    result = run_react_loop(chat_fn, "system prompt", "câu hỏi?", {})

    assert result == {"type": "unanswerable", "reason": "test"}
    tool_messages = [m for m in calls[1][0] if m.get("role") == "tool"]
    assert "error" in json.loads(tool_messages[0]["content"])


def test_malformed_submit_answer_arguments_returns_error_and_allows_retry():
    responses = [
        {"content": None, "tool_calls": [{"id": "1", "name": "submit_answer", "arguments": "not valid json"}]},
        {"content": None, "tool_calls": [{"id": "2", "name": "submit_answer", "arguments": '{"type": "boolean", "answer_json": "true"}'}]},
    ]
    chat_fn, calls = _make_chat_fn(responses)

    result = run_react_loop(chat_fn, "system prompt", "câu hỏi?", {})

    assert result == {"type": "boolean", "answer": True}


def test_exceeds_tool_call_budget_returns_unanswerable_without_extra_llm_call():
    responses = [
        {"content": None, "tool_calls": [{"id": str(i), "name": "khong_ton_tai", "arguments": "{}"}]}
        for i in range(MAX_TOOL_CALLS)
    ]
    chat_fn, calls = _make_chat_fn(responses)

    result = run_react_loop(chat_fn, "system prompt", "câu hỏi?", {})

    assert result == {"type": "unanswerable", "reason": "hết ngân sách bước suy luận"}
    assert len(calls) == MAX_TOOL_CALLS


def test_exceeds_time_budget_returns_unanswerable(monkeypatch):
    import reasoning_agent.react_loop as react_loop_module

    monkeypatch.setattr(react_loop_module, "TIME_BUDGET_SECONDS", 0.1)

    def slow_chat_fn(messages, tools, timeout):
        time.sleep(0.2)
        return {"content": "đang nghĩ...", "tool_calls": []}

    result = run_react_loop(slow_chat_fn, "system prompt", "câu hỏi?", {})

    assert result == {"type": "unanswerable", "reason": "hết ngân sách bước suy luận"}


def test_plain_text_response_gets_nudged_to_call_submit_answer():
    responses = [
        {"content": "Để tôi nghĩ thêm.", "tool_calls": []},
        {
            "content": None,
            "tool_calls": [{"id": "1", "name": "submit_answer", "arguments": '{"type": "string", "answer_json": "\\"ok\\""}'}],
        },
    ]
    chat_fn, calls = _make_chat_fn(responses)

    result = run_react_loop(chat_fn, "system prompt", "câu hỏi?", {})

    assert result == {"type": "string", "answer": "ok"}
    assert len(calls) == 2


def test_chat_fn_exception_returns_unanswerable_without_raising():
    def failing_chat_fn(messages, tools, timeout):
        raise RuntimeError("model server sập")

    result = run_react_loop(failing_chat_fn, "system prompt", "câu hỏi?", {})

    assert result == {"type": "unanswerable", "reason": "hết ngân sách bước suy luận"}
