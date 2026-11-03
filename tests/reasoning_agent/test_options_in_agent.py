import json
from datetime import date

from reasoning_agent.agent import answer_question
from reasoning_agent.options import AgentOptions

from .conftest import build_real_business


def _setup(tmp_path, monkeypatch):
    build_real_business(tmp_path, "biz_102")
    monkeypatch.setenv("REASONING_AGENT_MODEL", "fake-model")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://fake")


def _submit(config, messages, tools, timeout, **sampling):
    _submit.seen = {"messages": messages, "sampling": sampling}
    return {
        "content": None,
        "tool_calls": [
            {"id": "1", "name": "submit_answer", "arguments": json.dumps({"type": "number", "answer_json": "1"})}
        ],
    }


def test_sampling_and_prompt_extra_reach_the_model(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    monkeypatch.setattr("reasoning_agent.agent.call_chat_completion", _submit)

    options = AgentOptions(temperature=0.7, seed=43, prompt_extra_fn=lambda q: f"EXTRA-FOR::{q}")
    answer_question("Hôm qua bán mấy đơn?", "biz_102", date(2026, 3, 29), tmp_path, options=options)

    assert _submit.seen["sampling"] == {"temperature": 0.7, "seed": 43}
    system_prompt = _submit.seen["messages"][0]["content"]
    assert "EXTRA-FOR::Hôm qua bán mấy đơn?" in system_prompt


def test_default_options_keep_004_behavior(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    monkeypatch.setattr("reasoning_agent.agent.call_chat_completion", _submit)

    answer_question("Hôm qua bán mấy đơn?", "biz_102", date(2026, 3, 29), tmp_path)

    assert _submit.seen["sampling"] == {"temperature": 0.0, "seed": 42}
    assert "EXTRA-FOR" not in _submit.seen["messages"][0]["content"]


def test_semantic_tools_registered_only_when_enabled(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    seen = {}

    def chat(config, messages, tools, timeout, **sampling):
        seen["tools"] = {t["function"]["name"] for t in tools}
        seen["system"] = messages[0]["content"]
        return _submit(config, messages, tools, timeout, **sampling)

    monkeypatch.setattr("reasoning_agent.agent.call_chat_completion", chat)

    answer_question("q?", "biz_102", date(2026, 3, 29), tmp_path)
    assert "aggregate" not in seen["tools"]

    answer_question("q?", "biz_102", date(2026, 3, 29), tmp_path, options=AgentOptions(semantic_tools=True))
    assert {"aggregate", "percent_change"} <= seen["tools"]
    assert "Tool tổng hợp có sẵn" in seen["system"]
