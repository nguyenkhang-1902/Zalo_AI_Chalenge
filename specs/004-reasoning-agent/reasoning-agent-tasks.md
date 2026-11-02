# Reasoning Agent (004) — Tasks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans. Plan: `specs/004-reasoning-agent/reasoning-agent-plan.md`
> (đọc cả Global Constraints + Quyết định thiết kế bổ sung trước khi bắt đầu).

> ⚠️ **Trước khi dispatch Task 7**: cần 1 model server OpenAI-compatible THẬT đang chạy (vd
> `ollama serve` + model Qwen2.5-7B-Instruct đã pull) và env var `REASONING_AGENT_MODEL` +
> `REASONING_AGENT_BASE_URL` set đúng. Nếu chưa có — HỎI Khang trước khi dispatch, KHÔNG tự
> `ollama pull`/cài model mới (CLAUDE.md: máy 16GB, không tự cài lib/model nặng khi chưa hỏi).
> Task 1-6 không cần server thật (dùng fake HTTP server / fake chat_fn trong test).

---

### Task 1: `config.py` + `llm_client.py` — model-agnostic HTTP client (FR-007, FR-008)

**Files:**
- Create: `src/reasoning_agent/__init__.py` (rỗng, để package import được — nội dung thật thêm ở Task 6)
- Create: `src/reasoning_agent/config.py`
- Create: `src/reasoning_agent/llm_client.py`
- Test: `tests/reasoning_agent/__init__.py` (rỗng)
- Test: `tests/reasoning_agent/test_config.py`
- Test: `tests/reasoning_agent/test_llm_client.py`

**Interfaces:**
- Consumes: không có (task đầu tiên).
- Produces:
  - `AgentConfig` dataclass (`model: str`, `base_url: str`, `api_key: str`) — Task 6 dùng.
  - `load_config() -> AgentConfig` — Task 6 dùng.
  - `call_chat_completion(config: AgentConfig, messages: list[dict], tools: list[dict], timeout: float) -> dict`
    trả `{"content": str|None, "tool_calls": [{"id": str, "name": str, "arguments": str}]}` —
    Task 6 dùng làm `chat_fn` cho `react_loop.run_react_loop`.
  - `LLMClientError(Exception)` — Task 5 (react_loop) bắt exception này (và mọi exception khác)
    quanh lời gọi `chat_fn`.

- [ ] **Step 1: Tạo package rỗng**

```bash
mkdir -p src/reasoning_agent tests/reasoning_agent
touch src/reasoning_agent/__init__.py tests/reasoning_agent/__init__.py
```

- [ ] **Step 2: Viết test thất bại cho `config.py`**

Tạo `tests/reasoning_agent/test_config.py`:

```python
import pytest

from reasoning_agent.config import load_config


def test_raises_when_model_env_var_missing(monkeypatch):
    monkeypatch.delenv("REASONING_AGENT_MODEL", raising=False)
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://localhost:11434/v1")

    with pytest.raises(ValueError, match="REASONING_AGENT_MODEL"):
        load_config()


def test_raises_when_base_url_env_var_missing(monkeypatch):
    monkeypatch.setenv("REASONING_AGENT_MODEL", "qwen2.5:7b-instruct")
    monkeypatch.delenv("REASONING_AGENT_BASE_URL", raising=False)

    with pytest.raises(ValueError, match="REASONING_AGENT_BASE_URL"):
        load_config()


def test_loads_config_from_env_vars_and_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("REASONING_AGENT_MODEL", "qwen2.5:7b-instruct")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://localhost:11434/v1/")
    monkeypatch.setenv("REASONING_AGENT_API_KEY", "dummy-key")

    config = load_config()

    assert config.model == "qwen2.5:7b-instruct"
    assert config.base_url == "http://localhost:11434/v1"
    assert config.api_key == "dummy-key"


def test_api_key_defaults_to_empty_string(monkeypatch):
    monkeypatch.setenv("REASONING_AGENT_MODEL", "qwen2.5:7b-instruct")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.delenv("REASONING_AGENT_API_KEY", raising=False)

    config = load_config()

    assert config.api_key == ""
```

- [ ] **Step 3: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_config.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'reasoning_agent.config'`

- [ ] **Step 4: Viết `config.py`**

```python
"""Đọc model LLM đích qua env var — FR-007: tên/endpoint model KHÔNG hard-code ở bất kỳ đâu khác
trong source (SC-003 grep phải sạch)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    model: str
    base_url: str
    api_key: str


def load_config() -> AgentConfig:
    model = os.environ.get("REASONING_AGENT_MODEL", "").strip()
    base_url = os.environ.get("REASONING_AGENT_BASE_URL", "").strip()
    if not model:
        raise ValueError("Thiếu biến môi trường REASONING_AGENT_MODEL")
    if not base_url:
        raise ValueError("Thiếu biến môi trường REASONING_AGENT_BASE_URL")
    api_key = os.environ.get("REASONING_AGENT_API_KEY", "")
    return AgentConfig(model=model, base_url=base_url.rstrip("/"), api_key=api_key)
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/reasoning_agent/test_config.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/reasoning_agent/__init__.py src/reasoning_agent/config.py tests/reasoning_agent/__init__.py tests/reasoning_agent/test_config.py
git commit -m "feat: add model-agnostic config for reasoning agent (FR-007)"
```

- [ ] **Step 7: Viết test thất bại cho `llm_client.py` (dùng fake HTTP server, không gọi model thật)**

Tạo `tests/reasoning_agent/test_llm_client.py`:

```python
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
```

- [ ] **Step 8: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_llm_client.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'reasoning_agent.llm_client'`

- [ ] **Step 9: Viết `llm_client.py`**

```python
"""HTTP client OpenAI-compatible chat-completions, model-agnostic (FR-007/FR-008) — tương thích
vLLM/Ollama/llama.cpp vì đều expose `/chat/completions` theo chuẩn OpenAI function-calling.
temperature/seed là HẰNG SỐ ở đây (không qua env) — FR-008 chỉ yêu cầu giá trị thấp/0 + cố định,
không yêu cầu cấu hình được; chỉ model/endpoint mới bắt buộc qua env (FR-007)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from reasoning_agent.config import AgentConfig

TEMPERATURE = 0.0
SEED = 42


class LLMClientError(Exception):
    """Mọi lỗi giao tiếp với model server (timeout, lỗi HTTP, JSON phản hồi hỏng)."""


def call_chat_completion(
    config: AgentConfig,
    messages: list[dict],
    tools: list[dict],
    timeout: float,
) -> dict:
    body = {
        "model": config.model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": TEMPERATURE,
        "seed": SEED,
    }
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    request = urllib.request.Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise LLMClientError(str(e)) from e

    try:
        message: dict[str, Any] = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMClientError(f"Phản hồi model server không đúng format: {payload!r}") from e

    raw_tool_calls = message.get("tool_calls") or []
    tool_calls = [
        {"id": tc["id"], "name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
        for tc in raw_tool_calls
    ]
    return {"content": message.get("content"), "tool_calls": tool_calls}
```

- [ ] **Step 10: Chạy test, xác nhận PASS**

Run: `pytest tests/reasoning_agent/test_llm_client.py -v`
Expected: 5 passed

- [ ] **Step 11: Commit**

```bash
git add src/reasoning_agent/llm_client.py tests/reasoning_agent/test_llm_client.py
git commit -m "feat: add OpenAI-compatible chat-completions client for reasoning agent (FR-007, FR-008)"
```

---

### Task 2: `date_tools.py` — 12 tool date_resolver + guard `query_end` (FR-003, FR-004)

**Files:**
- Create: `src/reasoning_agent/react_loop.py` (CHỈ phần `ToolSpec` dataclass ở task này — phần
  `run_react_loop`/`submit_answer` thêm ở Task 5, cùng file)
- Create: `src/reasoning_agent/date_tools.py`
- Test: `tests/reasoning_agent/test_date_tools.py`

**Interfaces:**
- Consumes: `date_resolver` package (002, đã có) — 12 hàm công khai + `CalendarIndex`.
- Produces:
  - `ToolSpec` dataclass (`schema: dict`, `handler: Callable[..., dict]`) trong `react_loop.py` —
    Task 3/4/5/6 import từ đây.
  - `build_date_tool_registry(calendar_index: CalendarIndex, as_of_date: date) -> dict[str, ToolSpec]`
    — Task 6 dùng, key là đúng 12 tên tool: `today`, `n_days_ago`, `this_week`, `last_week`,
    `year_to_date`, `month_of`, `this_month`, `comparable_last_month`,
    `month_or_quarter_without_year`, `shift_session`, `tet_period`, `comparable_before_tet`.

- [ ] **Step 1: Tạo `react_loop.py` chỉ với `ToolSpec` (phần còn lại thêm ở Task 5)**

```python
"""Vòng ReAct — FR-005/FR-006. Phần ToolSpec tạo ở Task 2 để date_tools/sql_tool/schema_tools
dùng được; run_react_loop + submit_answer thêm ở Task 5."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolSpec:
    schema: dict
    handler: Callable[..., dict]
```

- [ ] **Step 2: Viết test thất bại cho `date_tools.py`**

Tạo `tests/reasoning_agent/test_date_tools.py` (dùng `train/calendar.csv` THẬT — Tết 2026 thật
theo file này là `2026-02-10..2026-02-26`, đã xác nhận bằng cách chạy `load_calendar` +
`tet_period` trực tiếp lúc viết plan):

```python
from datetime import date
from pathlib import Path

from date_resolver import load_calendar
from reasoning_agent.date_tools import build_date_tool_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _registry(as_of_date: date):
    calendar_index = load_calendar(str(PROJECT_ROOT / "train" / "calendar.csv"))
    return build_date_tool_registry(calendar_index, as_of_date)


def test_registry_has_all_12_date_tools():
    registry = _registry(date(2026, 6, 16))
    assert set(registry) == {
        "today", "n_days_ago", "this_week", "last_week", "year_to_date",
        "month_of", "this_month", "comparable_last_month",
        "month_or_quarter_without_year", "shift_session",
        "tet_period", "comparable_before_tet",
    }


def test_today_returns_query_end_equal_to_as_of_date():
    registry = _registry(date(2026, 6, 16))
    result = registry["today"].handler()
    assert result == {"start": "2026-06-16", "end": "2026-06-16", "query_end": "2026-06-16"}


def test_month_of_query_end_cuts_at_as_of_when_month_still_ongoing():
    # month_of trả CẢ kỳ (cả tháng 6, FR-004) -- query_end phải CẮT tại as_of vì tháng chưa hết.
    registry = _registry(date(2026, 6, 16))
    result = registry["month_of"].handler(month=6, year=2026)
    assert result["end"] == "2026-06-30"
    assert result["query_end"] == "2026-06-16"


def test_month_of_query_end_equals_end_when_month_already_fully_past():
    registry = _registry(date(2026, 6, 16))
    result = registry["month_of"].handler(month=3, year=2026)
    assert result["end"] == "2026-03-31"
    assert result["query_end"] == "2026-03-31"


def test_n_days_ago_counts_today_as_day_1():
    registry = _registry(date(2026, 6, 16))
    result = registry["n_days_ago"].handler(n=7)
    assert result == {"start": "2026-06-10", "end": "2026-06-16", "query_end": "2026-06-16"}


def test_shift_session_returns_session_label_not_date_range():
    registry = _registry(date(2026, 6, 16))
    assert registry["shift_session"].handler(hour=8) == {"session": "sáng"}
    assert registry["shift_session"].handler(hour=22) == {"session": None}


def test_tet_period_uses_real_calendar_csv_and_cuts_query_end_mid_period():
    registry = _registry(date(2026, 2, 15))
    result = registry["tet_period"].handler(year=2026)
    assert result["start"] == "2026-02-10"
    assert result["end"] == "2026-02-26"
    assert result["query_end"] == "2026-02-15"


def test_tet_period_returns_note_when_year_not_in_calendar():
    registry = _registry(date(2026, 6, 16))
    result = registry["tet_period"].handler(year=1900)
    assert result == {
        "start": None, "end": None, "query_end": None,
        "note": "không có dữ liệu lịch cho kỳ này",
    }


def test_month_or_quarter_without_year_raises_when_both_given_lets_exception_propagate():
    # date_resolver.month_or_quarter_without_year tự raise ValueError khi truyền cả 2 -- date_tools
    # KHÔNG tự bắt (dispatch wrapper của react_loop ở Task 5 mới là nơi bắt chung).
    registry = _registry(date(2026, 6, 16))
    try:
        registry["month_or_quarter_without_year"].handler(month=3, quarter=1)
        assert False, "phải raise ValueError"
    except ValueError:
        pass
```

- [ ] **Step 3: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_date_tools.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'reasoning_agent.date_tools'`

- [ ] **Step 4: Viết `date_tools.py`**

```python
"""Tool 1:1 với date_resolver — FR-003 (12 tool), FR-004 (query_end). shift_session không trả
start/end (hàm gốc không có khái niệm khoảng ngày) nên không áp guard query_end — xem Global
Constraints/plan "Đính chính lúc viết plan"."""
from __future__ import annotations

from datetime import date

from date_resolver import (
    CalendarIndex,
    comparable_before_tet,
    comparable_last_month,
    last_week,
    month_of,
    month_or_quarter_without_year,
    n_days_ago,
    shift_session,
    tet_period,
    this_month,
    this_week,
    today,
    year_to_date,
)

from reasoning_agent.react_loop import ToolSpec

_EMPTY_PARAMS = {"type": "object", "properties": {}, "required": []}


def _range_result(pair: tuple[date, date] | None, as_of_date: date) -> dict:
    if pair is None:
        return {"start": None, "end": None, "query_end": None, "note": "không có dữ liệu lịch cho kỳ này"}
    start, end = pair
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "query_end": min(end, as_of_date).isoformat(),
    }


def build_date_tool_registry(calendar_index: CalendarIndex, as_of_date: date) -> dict[str, ToolSpec]:
    return {
        "today": ToolSpec(
            schema={"name": "today", "description": "Hôm nay (as_of_date).", "parameters": _EMPTY_PARAMS},
            handler=lambda: _range_result(today(as_of_date), as_of_date),
        ),
        "n_days_ago": ToolSpec(
            schema={
                "name": "n_days_ago",
                "description": "N ngày gần nhất, kể cả hôm nay là ngày cuối (rulebook §2).",
                "parameters": {
                    "type": "object",
                    "properties": {"n": {"type": "integer", "description": "số ngày, >= 1"}},
                    "required": ["n"],
                },
            },
            handler=lambda n: _range_result(n_days_ago(as_of_date, n), as_of_date),
        ),
        "this_week": ToolSpec(
            schema={
                "name": "this_week",
                "description": "Tuần này: thứ Hai của tuần chứa hôm nay đến hết hôm nay.",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(this_week(as_of_date), as_of_date),
        ),
        "last_week": ToolSpec(
            schema={
                "name": "last_week",
                "description": "Tuần trước: cả tuần liền trước, thứ Hai đến Chủ nhật.",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(last_week(as_of_date), as_of_date),
        ),
        "year_to_date": ToolSpec(
            schema={
                "name": "year_to_date",
                "description": "Từ 01/01 năm nay đến hết hôm nay.",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(year_to_date(as_of_date), as_of_date),
        ),
        "month_of": ToolSpec(
            schema={
                "name": "month_of",
                "description": "Tháng M/Y: cả tháng, từ ngày 1 đến hết ngày cuối tháng.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "integer", "description": "1-12"},
                        "year": {"type": "integer"},
                    },
                    "required": ["month", "year"],
                },
            },
            handler=lambda month, year: _range_result(month_of(month, year), as_of_date),
        ),
        "this_month": ToolSpec(
            schema={
                "name": "this_month",
                "description": "Tháng này: từ ngày 1 đến hết hôm nay.",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(this_month(as_of_date), as_of_date),
        ),
        "comparable_last_month": ToolSpec(
            schema={
                "name": "comparable_last_month",
                "description": "Tháng trước, cùng số ngày với hôm nay (hết tháng trước nếu tháng trước không có ngày đó).",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(comparable_last_month(as_of_date), as_of_date),
        ),
        "month_or_quarter_without_year": ToolSpec(
            schema={
                "name": "month_or_quarter_without_year",
                "description": (
                    "Tháng M hoặc quý Q không ghi năm: của năm nay nếu không sau hôm nay, "
                    "sau hôm nay thì của năm trước. Truyền đúng 1 trong 2 tham số."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "integer", "description": "1-12, bỏ trống nếu dùng quarter"},
                        "quarter": {"type": "integer", "description": "1-4, bỏ trống nếu dùng month"},
                    },
                    "required": [],
                },
            },
            handler=lambda month=None, quarter=None: _range_result(
                month_or_quarter_without_year(as_of_date, month=month, quarter=quarter), as_of_date
            ),
        ),
        "shift_session": ToolSpec(
            schema={
                "name": "shift_session",
                "description": (
                    "Ca sáng (06:00-13:59) hoặc ca chiều (14:00-21:59) theo giờ tạo đơn. "
                    "Trả null nếu ngoài 2 ca."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"hour": {"type": "integer", "description": "giờ trong ngày, 0-23"}},
                    "required": ["hour"],
                },
            },
            handler=lambda hour: {"session": shift_session(hour)},
        ),
        "tet_period": ToolSpec(
            schema={
                "name": "tet_period",
                "description": (
                    "Dịp Tết năm âm Y: từ 23 tháng Chạp (năm âm Y-1) đến hết mùng 10 tháng Giêng "
                    "(năm âm Y), theo ngày dương, tra từ calendar.csv."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"year": {"type": "integer", "description": "năm âm lịch Y"}},
                    "required": ["year"],
                },
            },
            handler=lambda year: _range_result(tet_period(calendar_index, year), as_of_date),
        ),
        "comparable_before_tet": ToolSpec(
            schema={
                "name": "comparable_before_tet",
                "description": "Cùng số ngày ngay trước dịp Tết năm âm Y (để so sánh trước/sau Tết).",
                "parameters": {
                    "type": "object",
                    "properties": {"year": {"type": "integer", "description": "năm âm lịch Y"}},
                    "required": ["year"],
                },
            },
            handler=lambda year: _range_result(comparable_before_tet(calendar_index, year), as_of_date),
        ),
    }
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/reasoning_agent/test_date_tools.py -v`
Expected: 9 passed

- [ ] **Step 6: Commit**

```bash
git add src/reasoning_agent/react_loop.py src/reasoning_agent/date_tools.py tests/reasoning_agent/test_date_tools.py
git commit -m "feat: add date_resolver tool wrappers with query_end guard (FR-003, FR-004)"
```

---

### Task 3: `schema_tools.py` + `prompt.py` — get_readme/get_table_detail + system prompt (FR-002, FR-003)

**Files:**
- Create: `src/reasoning_agent/schema_tools.py`
- Create: `src/reasoning_agent/prompt.py`
- Create: `tests/reasoning_agent/conftest.py`
- Test: `tests/reasoning_agent/test_schema_tools_and_prompt.py`

**Interfaces:**
- Consumes: `ToolSpec` từ `reasoning_agent.react_loop` (Task 2); `data_loader.build_business_db.build_business`
  (001, đã có) — chỉ dùng trong test/conftest để build dữ liệu thật, KHÔNG trong source `reasoning_agent`.
- Produces:
  - `load_schema(dataset_dir: Path, business_id: str) -> dict` — Task 6 dùng.
  - `build_schema_tools(schema: dict) -> dict[str, ToolSpec]` — key `"get_readme"`, `"get_table_detail"` — Task 6 dùng.
  - `build_system_prompt(schema: dict, rulebook_text: str) -> str` — Task 6 dùng.
  - `build_real_business(dataset_dir: Path, business_id: str, copy_dataset_files: bool = True) -> None`
    trong `tests/reasoning_agent/conftest.py` — Task 4/6/7 import lại qua `from .conftest import build_real_business`.
  - `PROJECT_ROOT`, `TRAIN_DIR` trong `conftest.py` — Task 7 dùng.

- [ ] **Step 1: Viết `conftest.py` (helper build dữ liệu thật, không phải fixture giả)**

Tạo `tests/reasoning_agent/conftest.py`:

```python
"""Helper build dữ liệu thật cho test reasoning_agent — build qua chính
data_loader.build_business_db.build_business trên train/ thật, không dùng fixture bịa."""
from __future__ import annotations

import shutil
from pathlib import Path

from data_loader.build_business_db import build_business

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DIR = PROJECT_ROOT / "train"


def build_real_business(dataset_dir: Path, business_id: str, copy_dataset_files: bool = True) -> None:
    """Build thật 1 business từ train/data/<business_id> vào dataset_dir (thường tmp_path của
    test). copy_dataset_files=False khi test không cần rulebook.md/calendar.csv (schema_tools,
    sql_tool) -- chỉ cần=True cho test đụng agent.py (Task 6) hoặc react_loop đầy đủ."""
    if copy_dataset_files:
        for name in ("rulebook.md", "calendar.csv"):
            shutil.copy(TRAIN_DIR / name, dataset_dir / name)
    build_business(TRAIN_DIR / "data" / business_id, dataset_dir)
```

- [ ] **Step 2: Viết test thất bại cho `schema_tools.py` + `prompt.py`**

Tạo `tests/reasoning_agent/test_schema_tools_and_prompt.py` (dùng dữ liệu thật `train/data/biz_102`
— README/cột thật đã xác nhận: table `DonHang_ChiTiet` có 9 cột gồm `Mã đơn hàng`, `Ngày đặt hàng`,
`Trạng thái đơn hàng`, `Tên khách hàng`, `Tên sản phẩm`, `Số lượng sản phẩm`, `Giá sản phẩm`,
`Tổng tiền`, `Đơn vị tính`; `README.md` thật của biz_102 chứa chuỗi `"DonHang_ChiTiet.xlsx"`):

```python
import pytest

from reasoning_agent.prompt import build_system_prompt
from reasoning_agent.schema_tools import build_schema_tools, load_schema

from .conftest import build_real_business


def test_load_schema_reads_real_biz_102_schema_json(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)

    schema = load_schema(tmp_path, "biz_102")

    assert schema["business_id"] == "biz_102"
    table_names = {t["table_name"] for t in schema["tables"]}
    assert "DonHang_ChiTiet" in table_names


def test_get_readme_returns_real_readme_text(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    schema = load_schema(tmp_path, "biz_102")
    tools = build_schema_tools(schema)

    result = tools["get_readme"].handler()

    assert "DonHang_ChiTiet.xlsx" in result["readme"]


def test_get_table_detail_returns_real_columns(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    schema = load_schema(tmp_path, "biz_102")
    tools = build_schema_tools(schema)

    result = tools["get_table_detail"].handler(table_name="DonHang_ChiTiet")

    column_names = {c["name"] for c in result["columns"]}
    assert column_names == {
        "Mã đơn hàng", "Ngày đặt hàng", "Trạng thái đơn hàng", "Tên khách hàng",
        "Tên sản phẩm", "Số lượng sản phẩm", "Giá sản phẩm", "Tổng tiền", "Đơn vị tính",
    }


def test_get_table_detail_raises_for_unknown_table(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    schema = load_schema(tmp_path, "biz_102")
    tools = build_schema_tools(schema)

    with pytest.raises(ValueError, match="table không tồn tại"):
        tools["get_table_detail"].handler(table_name="khong_ton_tai")


def test_system_prompt_includes_table_names_and_rulebook_text(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    schema = load_schema(tmp_path, "biz_102")

    prompt = build_system_prompt(schema, rulebook_text="LUẬT RIÊNG: test marker 12345")

    assert "DonHang_ChiTiet" in prompt
    assert "LUẬT RIÊNG: test marker 12345" in prompt
    assert "query_end" in prompt
    assert "submit_answer" in prompt
```

- [ ] **Step 3: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_schema_tools_and_prompt.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'reasoning_agent.schema_tools'`

- [ ] **Step 4: Viết `schema_tools.py`**

```python
"""Tool đọc README/chi tiết table từ schema.json đã build sẵn — FR-002, FR-003."""
from __future__ import annotations

import json
from pathlib import Path

from reasoning_agent.react_loop import ToolSpec


def load_schema(dataset_dir: Path, business_id: str) -> dict:
    schema_path = dataset_dir / f"{business_id}.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def build_schema_tools(schema: dict) -> dict[str, ToolSpec]:
    tables_by_name = {t["table_name"]: t for t in schema["tables"]}

    def get_readme() -> dict:
        return {"readme": schema["readme"]}

    def get_table_detail(table_name: str) -> dict:
        table = tables_by_name.get(table_name)
        if table is None:
            raise ValueError(
                f"table không tồn tại: {table_name!r}. Các table có: {sorted(tables_by_name)}"
            )
        return {"table_name": table["table_name"], "columns": table["columns"]}

    return {
        "get_readme": ToolSpec(
            schema={
                "name": "get_readme",
                "description": "Đọc nguyên văn README.md của business này (quy ước dữ liệu, tên cột gốc).",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            handler=get_readme,
        ),
        "get_table_detail": ToolSpec(
            schema={
                "name": "get_table_detail",
                "description": "Đọc chi tiết đầy đủ 1 table: mọi cột kèm dtype, số dòng/null, mẫu giá trị thật.",
                "parameters": {
                    "type": "object",
                    "properties": {"table_name": {"type": "string"}},
                    "required": ["table_name"],
                },
            },
            handler=get_table_detail,
        ),
    }
```

- [ ] **Step 5: Viết `prompt.py`**

```python
"""Build system prompt mặc định — FR-002 (schema tóm tắt + rulebook nguyên văn, đọc runtime)."""
from __future__ import annotations


def build_system_prompt(schema: dict, rulebook_text: str) -> str:
    table_lines = []
    for table in schema["tables"]:
        columns = ", ".join(f"{c['name']} ({c['dtype']})" for c in table["columns"])
        table_lines.append(f"- {table['table_name']}: {columns}")
    tables_block = "\n".join(table_lines)

    return f"""Bạn là agent trả lời câu hỏi kinh doanh tiếng Việt cho 1 shop, dựa trên dữ liệu
DuckDB đã build sẵn. KHÔNG dùng hiểu biết bên ngoài — chỉ dùng dữ liệu đọc được qua tool.

## Các table có sẵn (tên bảng: tên cột (dtype))
{tables_block}

Gọi tool `get_table_detail` nếu cần xem mẫu giá trị thật của 1 table, hoặc `get_readme` nếu cần
đọc quy ước gốc của shop (tên cột gốc, cách quy đổi đơn vị...).

## Luật tính toán (rulebook.md của chính bộ dữ liệu này)
{rulebook_text}

## Cách dùng tool ngày (date_resolver)
Mọi tool ngày trả về CẢ kỳ qua `start`/`end` (kỳ đầy đủ theo rulebook §2, KHÔNG tự cắt tại hôm
nay) VÀ `query_end` (= `end` cắt tại hôm nay, chỉ khi kỳ còn đang diễn ra). Dùng `query_end` khi
lọc số liệu PHÁT SINH THỰC TẾ (doanh thu, số đơn...) của 1 kỳ đang diễn ra (vd "tháng này" khi
tháng chưa hết). Dùng `end` khi câu hỏi tự nó đã là 1 kỳ CỐ ĐỊNH trong quá khứ (vd "tháng 3/2026",
"đến hết ngày X" — câu hỏi "đến hết ngày X" đọc thẳng ngày X từ câu hỏi, KHÔNG cần gọi tool ngày
nào). `shift_session` không trả khoảng ngày (trả nhãn ca sáng/chiều theo giờ), không áp dụng
`query_end`.

## Kết thúc câu trả lời
Khi đã có đủ thông tin, PHẢI gọi tool `submit_answer` để đưa đáp án cuối cùng — không trả lời bằng
văn bản thường. `type` phải là 1 trong: number, percent, date, boolean, string, list, table,
unanswerable. `answer_json` là chuỗi JSON-encode giá trị đáp án tương ứng (vd `"4820000"` cho
number, `"[\\"Cà phê sữa\\"]"` cho list, `"{{\\"columns\\":[...],\\"rows\\":[...]}}"` cho table).
Nếu dữ liệu không đủ để trả lời theo rulebook mục 7, gọi `submit_answer` với `type="unanswerable"`
và `reason` giải thích ngắn."""
```

- [ ] **Step 6: Chạy test, xác nhận PASS**

Run: `pytest tests/reasoning_agent/test_schema_tools_and_prompt.py -v`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add src/reasoning_agent/schema_tools.py src/reasoning_agent/prompt.py tests/reasoning_agent/conftest.py tests/reasoning_agent/test_schema_tools_and_prompt.py
git commit -m "feat: add README/table-detail tools and system prompt builder (FR-002, FR-003)"
```

---

### Task 4: `sql_tool.py` — `run_sql` trên DuckDB read-only (FR-003)

**Files:**
- Create: `src/reasoning_agent/sql_tool.py`
- Test: `tests/reasoning_agent/test_sql_tool.py`

**Interfaces:**
- Consumes: `ToolSpec` (Task 2); `build_real_business` từ `tests/reasoning_agent/conftest.py` (Task 3).
- Produces: `build_sql_tool(conn: duckdb.DuckDBPyConnection) -> ToolSpec` (key `"run_sql"` khi
  Task 6 ghép vào registry) — trả `{"columns": [...], "rows": [[...], ...]}` hoặc `{"error": str}`.

- [ ] **Step 1: Viết test thất bại — dùng SQL thật đã verify kết quả đúng lúc viết plan**

Tạo `tests/reasoning_agent/test_sql_tool.py` (câu hỏi thật `train/questions.jsonl`
id=`q_06fad07d2128`: "Hôm qua cửa hàng bán được mấy đơn?" as_of_date=2026-03-29 → hôm qua =
2026-03-28; ground truth `train/answers.jsonl` = `73`; đã verify bằng cách build thật `biz_102` và
chạy đúng câu SQL dưới đây lúc viết plan, kết quả ra `73`):

```python
import duckdb

from reasoning_agent.sql_tool import build_sql_tool

from .conftest import build_real_business

_REAL_SQL = (
    'SELECT COUNT(DISTINCT "Mã đơn hàng") FROM DonHang_ChiTiet '
    "WHERE \"Ngày đặt hàng\" = DATE '2026-03-28' "
    "AND \"Trạng thái đơn hàng\" NOT IN ('Đã hủy', 'Đã hoàn hàng')"
)


def test_run_sql_on_real_biz_102_data_matches_ground_truth(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    conn = duckdb.connect(str(tmp_path / "biz_102.duckdb"), read_only=True)
    tool = build_sql_tool(conn)

    result = tool.handler(query=_REAL_SQL)

    assert result["rows"] == [[73]]
    conn.close()


def test_run_sql_returns_error_dict_on_bad_sql_without_raising(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    conn = duckdb.connect(str(tmp_path / "biz_102.duckdb"), read_only=True)
    tool = build_sql_tool(conn)

    result = tool.handler(query="SELECT * FROM table_khong_ton_tai")

    assert "error" in result
    conn.close()


def test_run_sql_returns_column_names(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    conn = duckdb.connect(str(tmp_path / "biz_102.duckdb"), read_only=True)
    tool = build_sql_tool(conn)

    result = tool.handler(query='SELECT "Mã đơn hàng" FROM DonHang_ChiTiet LIMIT 1')

    assert result["columns"] == ["Mã đơn hàng"]
    conn.close()


def test_run_sql_rejects_insert_on_read_only_connection_as_error_not_raise(tmp_path):
    # Edge case spec: INSERT/DROP trên connection read-only -> DuckDB tự raise lỗi quyền,
    # tool trả lỗi đó cho model như lỗi SQL thường (không có logic chặn riêng).
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    conn = duckdb.connect(str(tmp_path / "biz_102.duckdb"), read_only=True)
    tool = build_sql_tool(conn)

    result = tool.handler(query='INSERT INTO DonHang_ChiTiet VALUES (1)')

    assert "error" in result
    assert "read-only" in result["error"].lower() or "read_only" in result["error"].lower()
    conn.close()
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_sql_tool.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'reasoning_agent.sql_tool'`

- [ ] **Step 3: Viết `sql_tool.py`**

```python
"""Tool run_sql — FR-003, chạy trên DuckDB READ-ONLY, tự bắt lỗi DuckDB (yêu cầu rõ của FR-003:
'trả lỗi DuckDB nguyên văn, không raise')."""
from __future__ import annotations

import duckdb

from reasoning_agent.react_loop import ToolSpec


def build_sql_tool(conn: duckdb.DuckDBPyConnection) -> ToolSpec:
    def run_sql(query: str) -> dict:
        try:
            result = conn.execute(query)
            columns = [d[0] for d in result.description]
            rows = [list(row) for row in result.fetchall()]
            return {"columns": columns, "rows": rows}
        except Exception as e:
            return {"error": str(e)}

    return ToolSpec(
        schema={
            "name": "run_sql",
            "description": "Chạy 1 câu SELECT trên DuckDB của business này, trả về columns + rows.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Câu lệnh SQL SELECT"}},
                "required": ["query"],
            },
        },
        handler=run_sql,
    )
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `pytest tests/reasoning_agent/test_sql_tool.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/reasoning_agent/sql_tool.py tests/reasoning_agent/test_sql_tool.py
git commit -m "feat: add read-only run_sql tool for reasoning agent (FR-003)"
```

---

### Task 5: `react_loop.py` — vòng ReAct + `submit_answer` + ngân sách (FR-005, FR-006)

**Files:**
- Modify: `src/reasoning_agent/react_loop.py` (thêm `run_react_loop`, `_submit_answer_tool_spec`,
  `_dispatch`, constants — `ToolSpec` từ Task 2 giữ nguyên)
- Test: `tests/reasoning_agent/test_react_loop.py`

**Interfaces:**
- Consumes: `ToolSpec` (đã có, cùng file, từ Task 2).
- Produces: `run_react_loop(chat_fn: Callable[[list[dict], list[dict], float], dict], system_prompt: str, question: str, tool_registry: dict[str, ToolSpec]) -> dict`
  — Task 6 dùng, `chat_fn` nhận `(messages, tools, timeout)` (KHÔNG nhận `config` — Task 6 tự bind
  `config` bằng closure/lambda khi tạo `chat_fn`).
  `MAX_TOOL_CALLS = 6`, `TIME_BUDGET_SECONDS = 45.0` (module-level, Task 7 có thể đọc nếu cần đo).

- [ ] **Step 1: Viết test thất bại cho vòng ReAct (dùng chat_fn giả + tool giả, không đụng dữ liệu thật — test này kiểm cơ chế điều khiển luồng, không phải nghiệp vụ)**

Tạo `tests/reasoning_agent/test_react_loop.py`:

```python
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
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_react_loop.py -v`
Expected: FAIL với `ImportError: cannot import name 'run_react_loop' from 'reasoning_agent.react_loop'`

- [ ] **Step 3: Thêm phần vòng ReAct vào `react_loop.py` (file đã có `ToolSpec` từ Task 2, thêm phần dưới vào CUỐI file)**

```python
import json
import time
from typing import Any, Callable

MAX_TOOL_CALLS = 6
TIME_BUDGET_SECONDS = 45.0

_VALID_TYPES = {"number", "percent", "date", "boolean", "string", "list", "table", "unanswerable"}
_BUDGET_EXHAUSTED_RESULT = {"type": "unanswerable", "reason": "hết ngân sách bước suy luận"}


def _submit_answer_tool_spec() -> ToolSpec:
    def handler(type: str, answer_json: str = "null", reason: str | None = None) -> dict:
        if type not in _VALID_TYPES:
            raise ValueError(f"type không hợp lệ: {type!r}, phải là 1 trong {sorted(_VALID_TYPES)}")
        if type == "unanswerable":
            return {"type": "unanswerable", "reason": reason or ""}
        return {"type": type, "answer": json.loads(answer_json)}

    return ToolSpec(
        schema={
            "name": "submit_answer",
            "description": "Đưa đáp án cuối cùng và kết thúc. PHẢI gọi tool này để trả lời.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": sorted(_VALID_TYPES)},
                    "answer_json": {
                        "type": "string",
                        "description": 'Giá trị đáp án, JSON-encode thành chuỗi (vd "4820000", "[1,2]")',
                    },
                    "reason": {"type": "string", "description": "Chỉ dùng khi type=unanswerable"},
                },
                "required": ["type"],
            },
        },
        handler=handler,
    )


def _dispatch(name: str, raw_arguments: str, registry: dict[str, ToolSpec]) -> dict:
    spec = registry.get(name)
    if spec is None:
        return {"error": f"tool không tồn tại: {name}"}
    try:
        kwargs = json.loads(raw_arguments) if raw_arguments else {}
        return spec.handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


def run_react_loop(
    chat_fn: Callable[[list[dict], list[dict], float], dict],
    system_prompt: str,
    question: str,
    tool_registry: dict[str, ToolSpec],
) -> dict[str, Any]:
    registry = {**tool_registry, "submit_answer": _submit_answer_tool_spec()}
    tools_payload = [{"type": "function", "function": spec.schema} for spec in registry.values()]

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    tool_calls_used = 0
    start = time.monotonic()

    while True:
        remaining = TIME_BUDGET_SECONDS - (time.monotonic() - start)
        if remaining <= 0 or tool_calls_used >= MAX_TOOL_CALLS:
            return dict(_BUDGET_EXHAUSTED_RESULT)

        try:
            response = chat_fn(messages, tools_payload, remaining)
        except Exception:
            return dict(_BUDGET_EXHAUSTED_RESULT)

        raw_tool_calls = response.get("tool_calls") or []
        if not raw_tool_calls:
            messages.append({"role": "assistant", "content": response.get("content")})
            messages.append(
                {
                    "role": "user",
                    "content": "Bạn phải gọi tool submit_answer để đưa đáp án cuối cùng, không trả lời bằng văn bản thường.",
                }
            )
            continue

        messages.append(
            {
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": [
                    {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in raw_tool_calls
                ],
            }
        )

        for tool_call in raw_tool_calls:
            if tool_calls_used >= MAX_TOOL_CALLS:
                return dict(_BUDGET_EXHAUSTED_RESULT)
            tool_calls_used += 1

            result = _dispatch(tool_call["name"], tool_call["arguments"], registry)

            if tool_call["name"] == "submit_answer" and "error" not in result:
                return result

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
```

Lưu ý: `import json`, `import time`, `from typing import Any, Callable` ở Task 2 chưa có —
thêm vào đầu file cùng với các import đã có (`from dataclasses import dataclass`, `from typing
import Callable` — gộp 2 dòng `typing` import thành 1: `from typing import Any, Callable`).

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `pytest tests/reasoning_agent/test_react_loop.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/reasoning_agent/react_loop.py tests/reasoning_agent/test_react_loop.py
git commit -m "feat: add ReAct loop with submit_answer and step/time budget (FR-005, FR-006)"
```

---

### Task 6: `agent.py` — `answer_question()` wiring (FR-001, FR-009, SC-004, Edge cases)

**Files:**
- Create: `src/reasoning_agent/agent.py`
- Modify: `src/reasoning_agent/__init__.py` (re-export `answer_question`)
- Test: `tests/reasoning_agent/test_agent.py`

**Interfaces:**
- Consumes: TẤT CẢ sản phẩm Task 1-5 (`load_config`, `call_chat_completion`, `build_date_tool_registry`,
  `build_schema_tools`, `load_schema`, `build_system_prompt`, `build_sql_tool`, `run_react_loop`).
- Produces: `answer_question(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict` (FR-001) — public API của `004-reasoning-agent`, dùng trực tiếp ở Task 7.

- [ ] **Step 1: Viết test thất bại cho `agent.py`**

Tạo `tests/reasoning_agent/test_agent.py` (câu hỏi thật `train/questions.jsonl`
id=`q_06fad07d2128`, business `biz_102`, ground truth `train/answers.jsonl` = `73` — dùng fake
`chat_fn` mô phỏng đúng 1 lượt gọi `run_sql` thật rồi `submit_answer`, KHÔNG cần model server
thật cho task này; Task 7 mới chạy với model thật):

```python
import json
from datetime import date
from pathlib import Path

from reasoning_agent.agent import answer_question

from .conftest import build_real_business

_REAL_SQL = (
    'SELECT COUNT(DISTINCT "Mã đơn hàng") FROM DonHang_ChiTiet '
    "WHERE \"Ngày đặt hàng\" = DATE '2026-03-28' "
    "AND \"Trạng thái đơn hàng\" NOT IN ('Đã hủy', 'Đã hoàn hàng')"
)


def test_answer_question_on_real_train_question_biz_102(tmp_path, monkeypatch):
    build_real_business(tmp_path, "biz_102")
    monkeypatch.setenv("REASONING_AGENT_MODEL", "fake-model")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://fake")

    call_count = {"n": 0}

    def fake_chat_fn(config, messages, tools, timeout):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {
                "content": None,
                "tool_calls": [{"id": "1", "name": "run_sql", "arguments": json.dumps({"query": _REAL_SQL})}],
            }
        return {
            "content": None,
            "tool_calls": [
                {"id": "2", "name": "submit_answer", "arguments": json.dumps({"type": "number", "answer_json": "73"})}
            ],
        }

    monkeypatch.setattr("reasoning_agent.agent.call_chat_completion", fake_chat_fn)

    result = answer_question(
        question="Hôm qua cửa hàng bán được mấy đơn?",
        business_id="biz_102",
        as_of_date=date(2026, 3, 29),
        dataset_dir=tmp_path,
    )

    assert result == {"type": "number", "answer": 73}


def test_missing_rulebook_raises_at_init(tmp_path, monkeypatch):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    monkeypatch.setenv("REASONING_AGENT_MODEL", "fake-model")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://fake")

    try:
        answer_question("câu hỏi?", "biz_102", date(2026, 3, 29), tmp_path)
        assert False, "phải raise vì thiếu rulebook.md"
    except FileNotFoundError as e:
        assert "rulebook.md" in str(e)


def test_missing_calendar_raises_at_init(tmp_path, monkeypatch):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    import shutil

    from .conftest import TRAIN_DIR

    shutil.copy(TRAIN_DIR / "rulebook.md", tmp_path / "rulebook.md")  # có rulebook, thiếu calendar
    monkeypatch.setenv("REASONING_AGENT_MODEL", "fake-model")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://fake")

    try:
        answer_question("câu hỏi?", "biz_102", date(2026, 3, 29), tmp_path)
        assert False, "phải raise vì thiếu calendar.csv"
    except FileNotFoundError as e:
        assert "calendar.csv" in str(e)


def test_no_hardcoded_business_or_question_id_branching():
    src_dir = Path(__file__).resolve().parents[2] / "src" / "reasoning_agent"
    import re

    pattern = re.compile(r"business_id\s*==|question_id\s*==")
    offending = [f.name for f in src_dir.glob("*.py") if pattern.search(f.read_text(encoding="utf-8"))]
    assert offending == [], f"File rẽ nhánh theo business_id/question_id cụ thể: {offending}"


def test_no_hardcoded_model_name_in_source():
    src_dir = Path(__file__).resolve().parents[2] / "src" / "reasoning_agent"
    offending = [f.name for f in src_dir.glob("*.py") if "qwen" in f.read_text(encoding="utf-8").lower()]
    assert offending == [], f"File hard-code tên model: {offending}"
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_agent.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'reasoning_agent.agent'`

- [ ] **Step 3: Viết `agent.py`**

```python
"""Entry point FR-001 — wiring toàn bộ tool registry + system prompt + react loop cho 1 câu hỏi."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from date_resolver import load_calendar
from reasoning_agent.config import load_config
from reasoning_agent.date_tools import build_date_tool_registry
from reasoning_agent.llm_client import call_chat_completion
from reasoning_agent.prompt import build_system_prompt
from reasoning_agent.react_loop import run_react_loop
from reasoning_agent.schema_tools import build_schema_tools, load_schema
from reasoning_agent.sql_tool import build_sql_tool


def answer_question(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
    rulebook_path = dataset_dir / "rulebook.md"
    calendar_path = dataset_dir / "calendar.csv"
    if not rulebook_path.exists():
        raise FileNotFoundError(f"Thiếu rulebook.md trong {dataset_dir}")
    if not calendar_path.exists():
        raise FileNotFoundError(f"Thiếu calendar.csv trong {dataset_dir}")

    rulebook_text = rulebook_path.read_text(encoding="utf-8")
    calendar_index = load_calendar(str(calendar_path))
    schema = load_schema(dataset_dir, business_id)

    config = load_config()
    system_prompt = build_system_prompt(schema, rulebook_text)

    db_path = dataset_dir / f"{business_id}.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        registry = {
            **build_date_tool_registry(calendar_index, as_of_date),
            **build_schema_tools(schema),
            "run_sql": build_sql_tool(conn),
        }

        def chat_fn(messages: list[dict], tools: list[dict], timeout: float) -> dict:
            return call_chat_completion(config, messages, tools, timeout)

        return run_react_loop(chat_fn, system_prompt, question, registry)
    finally:
        conn.close()
```

- [ ] **Step 4: Cập nhật `__init__.py`**

```python
"""Reasoning agent — 004-reasoning-agent. Public API: answer_question (FR-001)."""
from __future__ import annotations

from reasoning_agent.agent import answer_question

__all__ = ["answer_question"]
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/reasoning_agent/test_agent.py -v`
Expected: 5 passed

- [ ] **Step 6: Chạy TOÀN BỘ test suite của `004` để xác nhận không có regression giữa các task**

Run: `pytest tests/reasoning_agent/ -v --ignore=tests/reasoning_agent/test_baseline_golden.py`
Expected: tất cả PASS (test_baseline_golden.py tạo ở Task 7, chưa tồn tại lúc này nên không cần `--ignore` thật sự — chỉ ghi chú để tránh nhầm khi Task 7 đã xong và re-run Task 6's test riêng)

- [ ] **Step 7: Commit**

```bash
git add src/reasoning_agent/agent.py src/reasoning_agent/__init__.py tests/reasoning_agent/test_agent.py
git commit -m "feat: wire answer_question entry point for reasoning agent (FR-001, SC-004)"
```

---

### Task 7: Baseline thật trên 100 câu hỏi mẫu (SC-001, SC-002, SC-005)

> ⚠️ Cần model server OpenAI-compatible THẬT đang chạy trước khi dispatch task này — xem ghi chú
> đầu file. Nếu chưa có, HỎI Khang, không tự cài/tải model.

**Files:**
- Test: `tests/reasoning_agent/test_baseline_golden.py`

**Interfaces:**
- Consumes: `answer_question` (Task 6), `score_submission`/`format_report` (003, đã có),
  `build_business` (001, đã có), `PROJECT_ROOT`/`TRAIN_DIR` (`tests/reasoning_agent/conftest.py`, Task 3).
- Produces: không có (task cuối, chỉ đo đạc + in báo cáo).

- [ ] **Step 1: Viết test (vừa là "test" vừa là script đo baseline — skip rõ ràng nếu thiếu model server, không fail cả suite)**

Tạo `tests/reasoning_agent/test_baseline_golden.py`:

```python
"""Task 7 — SC-001/SC-002: baseline thật trên 100 câu hỏi mẫu train/, cần model server
OpenAI-compatible THẬT đang chạy (set REASONING_AGENT_MODEL + REASONING_AGENT_BASE_URL)."""
from __future__ import annotations

import json
import os
import random
import shutil
import time
from datetime import date
from pathlib import Path

import pytest

from data_loader.build_business_db import build_business
from eval_harness.report import format_report
from eval_harness.scoring import score_submission
from reasoning_agent.agent import answer_question

from .conftest import TRAIN_DIR

_SAMPLE_SIZE = 100


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _stratified_sample(questions: list[dict], answers_by_id: dict, n: int) -> list[dict]:
    by_type: dict[str, list[dict]] = {}
    for q in questions:
        truth_type = answers_by_id[q["id"]]["type"]
        by_type.setdefault(truth_type, []).append(q)

    rng = random.Random(42)
    per_type = max(1, n // len(by_type))
    sampled: list[dict] = []
    for type_name in sorted(by_type):
        items = list(by_type[type_name])
        rng.shuffle(items)
        sampled.extend(items[:per_type])
    return sampled[:n]


@pytest.mark.skipif(
    not os.environ.get("REASONING_AGENT_MODEL") or not os.environ.get("REASONING_AGENT_BASE_URL"),
    reason="Cần REASONING_AGENT_MODEL + REASONING_AGENT_BASE_URL trỏ tới 1 model server thật đang chạy",
)
def test_baseline_accuracy_on_100_real_questions(tmp_path: Path):
    questions = _load_jsonl(TRAIN_DIR / "questions.jsonl")
    answers = _load_jsonl(TRAIN_DIR / "answers.jsonl")
    answers_by_id = {a["id"]: a for a in answers}

    sample = _stratified_sample(questions, answers_by_id, _SAMPLE_SIZE)
    business_ids = sorted({q["business_id"] for q in sample})

    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    shutil.copy(TRAIN_DIR / "rulebook.md", dataset_dir / "rulebook.md")
    shutil.copy(TRAIN_DIR / "calendar.csv", dataset_dir / "calendar.csv")
    for business_id in business_ids:
        build_business(TRAIN_DIR / "data" / business_id, dataset_dir)

    submission_path = tmp_path / "submission.jsonl"
    elapsed_per_question = []
    with submission_path.open("w", encoding="utf-8") as f:
        for q in sample:
            start = time.monotonic()
            result = answer_question(
                question=q["question"],
                business_id=q["business_id"],
                as_of_date=date.fromisoformat(q["as_of_date"]),
                dataset_dir=dataset_dir,
            )
            elapsed_per_question.append(time.monotonic() - start)
            f.write(json.dumps({"id": q["id"], **result}, ensure_ascii=False) + "\n")

    sample_questions_path = tmp_path / "sample_questions.jsonl"
    sample_answers_path = tmp_path / "sample_answers.jsonl"
    with sample_questions_path.open("w", encoding="utf-8") as f:
        for q in sample:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with sample_answers_path.open("w", encoding="utf-8") as f:
        for q in sample:
            f.write(json.dumps(answers_by_id[q["id"]], ensure_ascii=False) + "\n")

    report = score_submission(str(sample_questions_path), str(sample_answers_path), str(submission_path))
    print(format_report(report))

    assert all(e < 45.0 for e in elapsed_per_question), "Có câu vượt ngân sách 45s mà không rơi về unanswerable (SC-001)"
    assert report.accuracy > 0.0, "Baseline accuracy phải > 0% (SC-002)"

    avg_seconds = sum(elapsed_per_question) / len(elapsed_per_question)
    budget_per_question = (6 * 3600) / 1000  # SC-005: 6h / 1000 câu public_test, cận trên tạm tính
    print(f"Thời gian trung bình/câu: {avg_seconds:.1f}s (ngân sách tạm tính SC-005: {budget_per_question:.1f}s)")
```

- [ ] **Step 2: Xác nhận có model server thật đang chạy, set env var, chạy test**

```bash
# Ví dụ với Ollama đã pull qwen2.5:7b-instruct và đang `ollama serve`:
export REASONING_AGENT_MODEL=qwen2.5:7b-instruct
export REASONING_AGENT_BASE_URL=http://localhost:11434/v1
pytest tests/reasoning_agent/test_baseline_golden.py -v -s
```

Expected: 1 passed, output in ra `format_report(report)` thật (accuracy > 0%) + thời gian trung
bình/câu — đây là SỐ LIỆU THẬT để ghi vào `TIEN_DO.md`/`CHECKLIST-ZALO-DATAMATE-DUYET.md`, không
phải chỉ "test pass".

- [ ] **Step 3: Commit**

```bash
git add tests/reasoning_agent/test_baseline_golden.py
git commit -m "test: add real 100-question baseline accuracy measurement (SC-001, SC-002, SC-005)"
```

- [ ] **Step 4: Chạy lại TOÀN BỘ test suite dự án (không chỉ `reasoning_agent/`) để xác nhận không có regression**

Run: `pytest -v`
Expected: tất cả PASS (trừ `test_baseline_accuracy_on_100_real_questions` SKIP nếu không có model
server lúc chạy lại — đây là hành vi đúng theo thiết kế `skipif`, không phải lỗi).
