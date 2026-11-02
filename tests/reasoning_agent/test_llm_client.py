import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from reasoning_agent.config import AgentConfig
from reasoning_agent.llm_client import LLMClientError, call_chat_completion


class _FakeHandler(BaseHTTPRequestHandler):
    captured_body: dict | None = None
    captured_headers: dict | None = None
    response_body: dict = {}
    delay_seconds: float = 0.0

    def do_POST(self):
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        _FakeHandler.captured_body = json.loads(raw.decode("utf-8"))
        _FakeHandler.captured_headers = dict(self.headers)
        payload = json.dumps(_FakeHandler.response_body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def fake_server():
    server = HTTPServer(("127.0.0.1", 0), _FakeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    _FakeHandler.delay_seconds = 0.0
    yield port
    server.shutdown()
    thread.join()


def test_sends_model_agnostic_body_with_fixed_temperature_and_seed(fake_server):
    _FakeHandler.response_body = {"choices": [{"message": {"content": "xin chào", "tool_calls": []}}]}
    config = AgentConfig(model="qwen2.5:7b-instruct", base_url=f"http://127.0.0.1:{fake_server}", api_key="")

    result = call_chat_completion(config, messages=[{"role": "user", "content": "hi"}], tools=[], timeout=5.0)

    assert result == {"content": "xin chào", "tool_calls": []}
    body = _FakeHandler.captured_body
    assert body["model"] == "qwen2.5:7b-instruct"
    assert body["temperature"] == 0.0
    assert body["seed"] == 42
    assert body["tool_choice"] == "auto"


def test_parses_tool_calls_from_response(fake_server):
    _FakeHandler.response_body = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {"id": "call_1", "type": "function", "function": {"name": "today", "arguments": "{}"}}
                    ],
                }
            }
        ]
    }
    config = AgentConfig(model="qwen2.5:7b-instruct", base_url=f"http://127.0.0.1:{fake_server}", api_key="")

    result = call_chat_completion(config, messages=[], tools=[], timeout=5.0)

    assert result == {"content": None, "tool_calls": [{"id": "call_1", "name": "today", "arguments": "{}"}]}


def test_sends_bearer_header_when_api_key_set(fake_server):
    _FakeHandler.response_body = {"choices": [{"message": {"content": "ok", "tool_calls": []}}]}
    config = AgentConfig(model="m", base_url=f"http://127.0.0.1:{fake_server}", api_key="secret-key")

    call_chat_completion(config, messages=[], tools=[], timeout=5.0)

    assert _FakeHandler.captured_headers.get("Authorization") == "Bearer secret-key"


def test_omits_authorization_header_when_no_api_key(fake_server):
    _FakeHandler.response_body = {"choices": [{"message": {"content": "ok", "tool_calls": []}}]}
    config = AgentConfig(model="m", base_url=f"http://127.0.0.1:{fake_server}", api_key="")

    call_chat_completion(config, messages=[], tools=[], timeout=5.0)

    assert "Authorization" not in _FakeHandler.captured_headers


def test_raises_llm_client_error_on_timeout(fake_server):
    _FakeHandler.response_body = {"choices": [{"message": {"content": "ok", "tool_calls": []}}]}
    _FakeHandler.delay_seconds = 1.0
    config = AgentConfig(model="m", base_url=f"http://127.0.0.1:{fake_server}", api_key="")

    with pytest.raises(LLMClientError):
        call_chat_completion(config, messages=[], tools=[], timeout=0.1)
