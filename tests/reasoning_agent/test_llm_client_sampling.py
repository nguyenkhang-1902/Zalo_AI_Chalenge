import json

from reasoning_agent.config import AgentConfig
from reasoning_agent.llm_client import call_chat_completion


class _Resp:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _capture(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured.update(json.loads(request.data.decode("utf-8")))
        return _Resp({"choices": [{"message": {"content": "x"}}]})

    monkeypatch.setattr("reasoning_agent.llm_client.urllib.request.urlopen", fake_urlopen)
    return captured


def test_sampling_params_are_forwarded(monkeypatch):
    captured = _capture(monkeypatch)
    call_chat_completion(AgentConfig("m", "http://x", ""), [], [], 5.0, temperature=0.7, seed=9)
    assert captured["temperature"] == 0.7
    assert captured["seed"] == 9


def test_defaults_unchanged(monkeypatch):
    captured = _capture(monkeypatch)
    call_chat_completion(AgentConfig("m", "http://x", ""), [], [], 5.0)
    assert captured["temperature"] == 0.0
    assert captured["seed"] == 42
