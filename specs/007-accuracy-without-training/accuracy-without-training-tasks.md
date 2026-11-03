# Accuracy Without Training (007) — Tasks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) hoặc superpowers:executing-plans. Plan: `specs/007-accuracy-without-training/accuracy-without-training-plan.md`
> (đọc Global Constraints + Quyết định thiết kế bổ sung trước khi bắt đầu).

> ⚠️ **Task 6 cần model server thật** (Ollama + `qwen2.5-7b-ctx12k` đã có) và, cho bước 14B,
> phải HỎI Khang trước khi tải GGUF (~9GB). Task 1–5 chỉ dùng fake, không cần server.

---

### Task 1: `AgentOptions` + sampling params + sửa `json.dumps` (nền cho mọi đòn bẩy)

**Files:**
- Create: `src/reasoning_agent/options.py`
- Modify: `src/reasoning_agent/llm_client.py` (hàm `call_chat_completion`)
- Modify: `src/reasoning_agent/prompt.py` (thêm tham số `extra`)
- Modify: `src/reasoning_agent/react_loop.py` (hằng `BUDGET_EXHAUSTED_REASON`, `default=str`)
- Modify: `src/reasoning_agent/agent.py`
- Modify: `tests/reasoning_agent/test_agent.py` (chữ ký fake_chat_fn)
- Test: `tests/reasoning_agent/test_llm_client_sampling.py`, `tests/reasoning_agent/test_options_in_agent.py`, `tests/reasoning_agent/test_react_loop_serialization.py`

**Interfaces:**
- Produces:
  - `AgentOptions(temperature: float = TEMPERATURE, seed: int = SEED, semantic_tools: bool = False,
    prompt_extra_fn: Callable[[str], str] | None = None)` (frozen dataclass) — Task 3/4/5 dùng.
  - `call_chat_completion(config, messages, tools, timeout, temperature=TEMPERATURE, seed=SEED)`.
  - `build_system_prompt(schema, rulebook_text, extra="")`.
  - `answer_question(question, business_id, as_of_date, dataset_dir, options: AgentOptions | None = None) -> dict`.
  - `react_loop.BUDGET_EXHAUSTED_REASON: str` — Task 2 dùng.

- [ ] **Step 1: Viết test `call_chat_completion` truyền temperature/seed**

`tests/reasoning_agent/test_llm_client_sampling.py`:

```python
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
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_llm_client_sampling.py -v`
Expected: `test_sampling_params_are_forwarded` FAIL (`TypeError: unexpected keyword argument 'temperature'`).

- [ ] **Step 3: Sửa `llm_client.py`**

Thay chữ ký + body:

```python
def call_chat_completion(
    config: AgentConfig,
    messages: list[dict],
    tools: list[dict],
    timeout: float,
    temperature: float = TEMPERATURE,
    seed: int = SEED,
) -> dict:
    body = {
        "model": config.model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": temperature,
        "seed": seed,
    }
```
(phần còn lại của hàm giữ nguyên.)

- [ ] **Step 4: Viết test `react_loop` chịu được `Decimal`/`date` + hằng budget**

`tests/reasoning_agent/test_react_loop_serialization.py`:

```python
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
```

- [ ] **Step 5: Sửa `react_loop.py`**

Thay 2 dòng định nghĩa `_BUDGET_EXHAUSTED_RESULT`:

```python
BUDGET_EXHAUSTED_REASON = "hết ngân sách bước suy luận"
_BUDGET_EXHAUSTED_RESULT = {"type": "unanswerable", "reason": BUDGET_EXHAUSTED_REASON}
```
và trong vòng lặp, đổi `json.dumps(result, ensure_ascii=False)` thành
`json.dumps(result, ensure_ascii=False, default=str)`.

- [ ] **Step 6: Tạo `options.py`**

```python
"""Tuỳ chọn biến thể hoá 1 lần chạy answer_question (007) — mặc định giữ nguyên hành vi 004."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from reasoning_agent.llm_client import SEED, TEMPERATURE


@dataclass(frozen=True)
class AgentOptions:
    temperature: float = TEMPERATURE
    seed: int = SEED
    semantic_tools: bool = False
    prompt_extra_fn: Callable[[str], str] | None = None
```

- [ ] **Step 7: Viết test agent dùng options**

`tests/reasoning_agent/test_options_in_agent.py`:

```python
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
```

- [ ] **Step 8: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_options_in_agent.py -v`
Expected: FAIL (`unexpected keyword argument 'options'`).

- [ ] **Step 9: Sửa `prompt.py`**

Đổi chữ ký và return:

```python
def build_system_prompt(schema: dict, rulebook_text: str, extra: str = "") -> str:
```
Thêm ngay trước `return f"""...` : giữ nguyên f-string, rồi gán `prompt = f"""..."""` và cuối hàm
`return f"{prompt}\n\n{extra}" if extra else prompt`. (Tức đổi `return f"""` thành `prompt = f"""`.)

- [ ] **Step 10: Sửa `agent.py`**

Thay toàn bộ phần sau dòng `schema = load_schema(...)`:

```python
    config = load_config()
    options = options or AgentOptions()
    extra = options.prompt_extra_fn(question) if options.prompt_extra_fn else ""
    system_prompt = build_system_prompt(schema, rulebook_text, extra)

    db_path = dataset_dir / f"{business_id}.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        registry = {
            **build_date_tool_registry(calendar_index, as_of_date),
            **build_schema_tools(schema),
            "run_sql": build_sql_tool(conn),
        }

        def chat_fn(messages: list[dict], tools: list[dict], timeout: float) -> dict:
            return call_chat_completion(
                config, messages, tools, timeout, temperature=options.temperature, seed=options.seed
            )

        return run_react_loop(chat_fn, system_prompt, question, registry)
    finally:
        conn.close()
```
và đổi chữ ký hàm thành
`def answer_question(question, business_id, as_of_date, dataset_dir, options: AgentOptions | None = None) -> dict:`,
thêm `from reasoning_agent.options import AgentOptions`.
(`semantic_tools` được nối dây ở Task 4.)

- [ ] **Step 11: Cập nhật fake cũ trong `tests/reasoning_agent/test_agent.py`**

Mọi `def fake_chat_fn(config, messages, tools, timeout):` đổi thành
`def fake_chat_fn(config, messages, tools, timeout, **sampling):`. Kiểm tra thêm:
`grep -rn "call_chat_completion" tests/` và sửa mọi fake khác cùng kiểu.

- [ ] **Step 12: Chạy cả bộ test reasoning_agent**

Run: `pytest tests/reasoning_agent -q --ignore=tests/reasoning_agent/test_baseline_golden.py`
Expected: toàn bộ PASS (40 cũ + test mới).

- [ ] **Step 13: Commit**

```bash
git add src/reasoning_agent tests/reasoning_agent
git commit -m "feat: add AgentOptions with sampling params and serialize non-JSON tool results"
```

---

### Task 2: `consensus.py` — bỏ phiếu, quyết định abstain, đường cong PA (US1, FR-001/FR-002)

**Files:**
- Create: `src/accuracy_boost/__init__.py` (rỗng)
- Create: `src/accuracy_boost/consensus.py`
- Test: `tests/accuracy_boost/__init__.py` (rỗng), `tests/accuracy_boost/test_consensus.py`

**Interfaces:**
- Consumes: `reasoning_agent.react_loop.BUDGET_EXHAUSTED_REASON`; `eval_harness.matchers.is_correct(truth_type, predicted, truth_answer, alias)`.
- Produces:
  - `answer_key(result: dict) -> str` — khoá so khớp; `"abstain"` cho phiếu abstain.
  - `Decision(result: dict | None, agreement: float)` (frozen dataclass); `result is None` = abstain.
  - `decide(results: list[dict], threshold: float) -> Decision`.
  - `pa_curve(runs_by_id: dict[str, list[dict]], answers_by_id: dict[str, dict], thresholds: list[float]) -> list[dict]`
    mỗi phần tử `{"threshold", "pa", "correct", "wrong", "abstained"}`.

- [ ] **Step 1: Viết test**

`tests/accuracy_boost/test_consensus.py`:

```python
from accuracy_boost.consensus import answer_key, decide, pa_curve
from reasoning_agent.react_loop import BUDGET_EXHAUSTED_REASON

A = {"type": "number", "answer": 100.0}
A_NEAR = {"type": "number", "answer": 100.001}
B = {"type": "number", "answer": 200}
C = {"type": "string", "answer": "Cà phê"}
BUDGET = {"type": "unanswerable", "reason": BUDGET_EXHAUSTED_REASON}
ABSTAIN = {"type": "abstain"}


def test_numbers_equal_after_rounding_to_two_decimals():
    assert answer_key(A) == answer_key(A_NEAR)
    assert answer_key(A) != answer_key(B)


def test_string_key_ignores_case_and_spacing_but_keeps_diacritics():
    assert answer_key({"type": "string", "answer": " Cà  Phê "}) == answer_key(C.copy() | {"answer": "cà phê"})
    assert answer_key({"type": "string", "answer": "ca phe"}) != answer_key(C)


def test_table_rows_compared_as_a_set():
    t1 = {"type": "table", "answer": {"columns": ["a"], "rows": [[1], [2]]}}
    t2 = {"type": "table", "answer": {"columns": ["a"], "rows": [[2], [1]]}}
    assert answer_key(t1) == answer_key(t2)


def test_budget_exhausted_and_abstain_are_abstain_votes():
    assert answer_key(BUDGET) == "abstain"
    assert answer_key(ABSTAIN) == "abstain"
    assert answer_key({"type": "unanswerable", "reason": "thiếu giá vốn"}) == "unanswerable"


def test_majority_above_threshold_is_returned():
    decision = decide([A, B, A_NEAR], threshold=0.6)
    assert decision.result == A
    assert round(decision.agreement, 2) == 0.67


def test_no_majority_abstains():
    assert decide([A, B, C], threshold=0.6).result is None


def test_tie_prefers_first_run():
    assert decide([B, A], threshold=0.5).result == B


def test_abstain_votes_never_win_but_lower_agreement():
    assert decide([BUDGET, BUDGET, A], threshold=0.6).result is None
    assert decide([BUDGET, BUDGET, A], threshold=0.3).result == A
    assert decide([BUDGET, ABSTAIN], threshold=0.0).result is None


def test_pa_curve_scores_plus_minus_and_abstain():
    answers = {
        "q1": {"type": "number", "answer": 100, "alias": []},
        "q2": {"type": "number", "answer": 5, "alias": []},
    }
    runs = {"q1": [A, A, A], "q2": [A, B, C]}
    rows = pa_curve(runs, answers, [0.3, 1.0])
    low, high = rows
    assert (low["correct"], low["wrong"], low["abstained"]) == (1, 1, 0)
    assert low["pa"] == 0.0
    assert (high["correct"], high["wrong"], high["abstained"]) == (1, 0, 1)
    assert high["pa"] == 0.5
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/accuracy_boost/test_consensus.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'accuracy_boost'`.

- [ ] **Step 3: Viết `consensus.py`**

```python
"""Bỏ phiếu giữa N lần chạy → đáp án hoặc abstain (US1) + đường cong PA theo ngưỡng (FR-002).

Phiếu "hết ngân sách" của 004 là abstain chứ không phải unanswerable: với PA, trả unanswerable
sai tốn -1."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass

from eval_harness.matchers import is_correct
from reasoning_agent.react_loop import BUDGET_EXHAUSTED_REASON

ABSTAIN_KEY = "abstain"


@dataclass(frozen=True)
class Decision:
    result: dict | None
    agreement: float


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def answer_key(result: dict) -> str:
    result_type = result.get("type")
    if result_type == "abstain":
        return ABSTAIN_KEY
    if result_type == "unanswerable":
        return ABSTAIN_KEY if result.get("reason") == BUDGET_EXHAUSTED_REASON else "unanswerable"

    answer = result.get("answer")
    if result_type in ("number", "percent") and _is_number(answer):
        return f"{result_type}:{round(float(answer), 2)}"
    if result_type == "string" and isinstance(answer, str):
        return f"string:{' '.join(answer.lower().split())}"
    if result_type == "table" and isinstance(answer, dict):
        rows = sorted(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in answer.get("rows") or [])
        return "table:" + json.dumps({"columns": answer.get("columns"), "rows": rows}, ensure_ascii=False)
    return f"{result_type}:" + json.dumps(answer, ensure_ascii=False, sort_keys=True, default=str)


def decide(results: list[dict], threshold: float) -> Decision:
    if not results:
        raise ValueError("decide cần ít nhất 1 kết quả")
    keys = [answer_key(r) for r in results]
    counts = Counter(k for k in keys if k != ABSTAIN_KEY)
    if not counts:
        return Decision(None, 0.0)

    best = max(counts.values())
    winner_key = next(k for k in keys if counts.get(k) == best)
    agreement = best / len(results)
    if agreement + 1e-9 < threshold:
        return Decision(None, agreement)
    return Decision(results[keys.index(winner_key)], agreement)


def pa_curve(
    runs_by_id: dict[str, list[dict]], answers_by_id: dict[str, dict], thresholds: list[float]
) -> list[dict]:
    rows = []
    for threshold in thresholds:
        correct = wrong = abstained = 0
        for question_id, results in runs_by_id.items():
            decision = decide(results, threshold)
            if decision.result is None:
                abstained += 1
                continue
            truth = answers_by_id[question_id]
            if is_correct(truth["type"], decision.result, truth.get("answer"), truth.get("alias")):
                correct += 1
            else:
                wrong += 1
        total = len(runs_by_id)
        rows.append(
            {
                "threshold": threshold,
                "pa": (correct - wrong) / total if total else 0.0,
                "correct": correct,
                "wrong": wrong,
                "abstained": abstained,
            }
        )
    return rows
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `pytest tests/accuracy_boost/test_consensus.py -v`
Expected: 8 PASS. (Nếu `test_string_key...` lỗi do dict-union `|`, thay bằng `{**C, "answer": "cà phê"}`.)

- [ ] **Step 5: Commit**

```bash
git add src/accuracy_boost tests/accuracy_boost
git commit -m "feat: add consensus voting and PA-by-threshold curve for confidence gate"
```

---

### Task 3: Gated agent + DevSet + measure + runner bỏ dòng abstain (US1, FR-001/002/007/010)

**Files:**
- Create: `src/accuracy_boost/config.py`
- Create: `src/accuracy_boost/gated.py`
- Create: `src/accuracy_boost/devset.py`
- Create: `src/accuracy_boost/measure.py`
- Modify: `src/answer_formatter/runner.py`
- Test: `tests/accuracy_boost/test_config.py`, `test_gated.py`, `test_devset.py`, `test_measure.py`, `tests/answer_formatter/test_runner_abstain.py`

**Interfaces:**
- Consumes: Task 1 `AgentOptions`; Task 2 `decide`, `pa_curve`.
- Produces:
  - `BoostConfig(n_runs: int, threshold: float, sample_temperature: float, base_seed: int)` + `load_boost_config() -> BoostConfig`
    (env `ACCURACY_BOOST_N_RUNS`=3, `_THRESHOLD`=0.6, `_SAMPLE_TEMPERATURE`=0.7, `_BASE_SEED`=42).
  - `options_for_run(base: AgentOptions, run_index: int, sample_temperature: float) -> AgentOptions`.
  - `answer_with_gate(question, business_id, as_of_date, dataset_dir, *, n_runs, threshold, sample_temperature, base_options=None, run_fn=answer_question) -> dict` (trả `{"type": "abstain"}` khi abstain).
  - `make_gated_answer_fn(**kwargs) -> Callable[[str, str, date, Path], dict]` — truyền được vào `run_batch(answer_fn=...)`.
  - `build_devset(questions, answers_by_id, size=200, seed=42, min_per_type=2) -> list[dict]`; `take_subset(devset, n, seed=42) -> list[dict]`.
  - `prepare_dataset_dir(train_dir, business_ids, dataset_dir) -> None`;
    `collect_runs(devset, dataset_dir, out_path, *, n_runs, sample_temperature, base_options, run_fn=answer_question) -> int`;
    `load_runs(path) -> dict[str, list[dict]]`; `format_curve(rows) -> str`; `main(argv=None) -> int`.

- [ ] **Step 1: Test config**

`tests/accuracy_boost/test_config.py`:

```python
from accuracy_boost.config import load_boost_config


def test_defaults(monkeypatch):
    for name in ("N_RUNS", "THRESHOLD", "SAMPLE_TEMPERATURE", "BASE_SEED"):
        monkeypatch.delenv(f"ACCURACY_BOOST_{name}", raising=False)
    cfg = load_boost_config()
    assert (cfg.n_runs, cfg.threshold, cfg.sample_temperature, cfg.base_seed) == (3, 0.6, 0.7, 42)


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("ACCURACY_BOOST_N_RUNS", "5")
    monkeypatch.setenv("ACCURACY_BOOST_THRESHOLD", "0.8")
    cfg = load_boost_config()
    assert cfg.n_runs == 5 and cfg.threshold == 0.8
```

- [ ] **Step 2: Viết `config.py`**

```python
"""Tham số cổng tin cậy — Điều 4: mọi ngưỡng ở config/env, không magic value."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BoostConfig:
    n_runs: int
    threshold: float
    sample_temperature: float
    base_seed: int


def load_boost_config() -> BoostConfig:
    return BoostConfig(
        n_runs=int(os.environ.get("ACCURACY_BOOST_N_RUNS", "3")),
        threshold=float(os.environ.get("ACCURACY_BOOST_THRESHOLD", "0.6")),
        sample_temperature=float(os.environ.get("ACCURACY_BOOST_SAMPLE_TEMPERATURE", "0.7")),
        base_seed=int(os.environ.get("ACCURACY_BOOST_BASE_SEED", "42")),
    )
```

- [ ] **Step 3: Test gated**

`tests/accuracy_boost/test_gated.py`:

```python
from datetime import date
from pathlib import Path

import pytest

from accuracy_boost.gated import answer_with_gate, make_gated_answer_fn, options_for_run
from reasoning_agent.options import AgentOptions

A = {"type": "number", "answer": 1}
B = {"type": "number", "answer": 2}


def _scripted(results):
    calls = []

    def run_fn(question, business_id, as_of_date, dataset_dir, options):
        calls.append(options)
        return results[len(calls) - 1]

    run_fn.calls = calls
    return run_fn


def test_run_zero_is_greedy_and_others_sample_with_distinct_seeds():
    base = AgentOptions(seed=42)
    assert options_for_run(base, 0, 0.7).temperature == 0.0
    assert options_for_run(base, 0, 0.7).seed == 42
    assert options_for_run(base, 2, 0.7).temperature == 0.7
    assert options_for_run(base, 2, 0.7).seed == 44


def test_returns_majority_answer():
    run_fn = _scripted([A, B, A])
    result = answer_with_gate("q", "b", date(2026, 1, 1), Path("."), n_runs=3, threshold=0.6, sample_temperature=0.7, run_fn=run_fn)
    assert result == A
    assert len(run_fn.calls) == 3


def test_abstains_without_agreement():
    run_fn = _scripted([A, B, {"type": "string", "answer": "x"}])
    result = answer_with_gate("q", "b", date(2026, 1, 1), Path("."), n_runs=3, threshold=0.6, sample_temperature=0.7, run_fn=run_fn)
    assert result == {"type": "abstain"}


def test_run_exception_counts_as_abstain_vote_but_missing_files_propagate():
    def flaky(question, business_id, as_of_date, dataset_dir, options):
        if options.seed == 43:
            raise RuntimeError("boom")
        return A

    result = answer_with_gate("q", "b", date(2026, 1, 1), Path("."), n_runs=3, threshold=0.6, sample_temperature=0.7, base_options=AgentOptions(seed=42), run_fn=flaky)
    assert result == A

    def infra(question, business_id, as_of_date, dataset_dir, options):
        raise FileNotFoundError("rulebook.md")

    with pytest.raises(FileNotFoundError):
        answer_with_gate("q", "b", date(2026, 1, 1), Path("."), n_runs=3, threshold=0.6, sample_temperature=0.7, run_fn=infra)


def test_make_gated_answer_fn_matches_runner_signature():
    fn = make_gated_answer_fn(n_runs=2, threshold=0.5, sample_temperature=0.7, run_fn=_scripted([A, A]))
    assert fn("q", "b", date(2026, 1, 1), Path(".")) == A
```

- [ ] **Step 4: Viết `gated.py`**

```python
"""Chạy N lần → đáp án đồng thuận hoặc abstain (US1). Run 0 greedy, run i≥1 lấy mẫu với seed
base+i (FR-010: tất định theo chỉ số lần chạy, không theo question_id)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Callable

from accuracy_boost.consensus import decide
from reasoning_agent import answer_question
from reasoning_agent.options import AgentOptions

ABSTAIN = {"type": "abstain"}


def options_for_run(base: AgentOptions, run_index: int, sample_temperature: float) -> AgentOptions:
    temperature = 0.0 if run_index == 0 else sample_temperature
    return replace(base, temperature=temperature, seed=base.seed + run_index)


def answer_with_gate(
    question: str,
    business_id: str,
    as_of_date: date,
    dataset_dir: Path,
    *,
    n_runs: int,
    threshold: float,
    sample_temperature: float,
    base_options: AgentOptions | None = None,
    run_fn: Callable[..., dict] = answer_question,
) -> dict:
    base = base_options or AgentOptions()
    results: list[dict] = []
    for run_index in range(n_runs):
        options = options_for_run(base, run_index, sample_temperature)
        try:
            results.append(run_fn(question, business_id, as_of_date, dataset_dir, options=options))
        except FileNotFoundError:
            raise
        except Exception:  # noqa: BLE001 - 1 lần chạy lỗi chỉ là 1 phiếu abstain
            results.append(dict(ABSTAIN))
    decision = decide(results, threshold)
    return decision.result if decision.result is not None else dict(ABSTAIN)


def make_gated_answer_fn(**kwargs) -> Callable[[str, str, date, Path], dict]:
    def answer_fn(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
        return answer_with_gate(question, business_id, as_of_date, dataset_dir, **kwargs)

    return answer_fn
```

Lưu ý: `reasoning_agent/__init__.py` đã export `answer_question` (005 import `from reasoning_agent import answer_question`).

- [ ] **Step 5: Test devset**

`tests/accuracy_boost/test_devset.py`:

```python
from accuracy_boost.devset import build_devset, take_subset


def _data(counts):
    questions, answers = [], {}
    for type_name, n in counts.items():
        for i in range(n):
            qid = f"{type_name}_{i:03d}"
            questions.append({"id": qid, "business_id": "b", "question": qid, "as_of_date": "2026-01-01"})
            answers[qid] = {"type": type_name}
    return questions, answers


def test_stratified_exact_size_and_min_per_type():
    questions, answers = _data({"number": 600, "percent": 300, "table": 5, "boolean": 4})
    dev = build_devset(questions, answers, size=100, seed=1, min_per_type=2)
    assert len(dev) == 100
    types = [answers[q["id"]]["type"] for q in dev]
    assert types.count("table") >= 2 and types.count("boolean") >= 2
    assert types.count("number") > types.count("percent")


def test_deterministic_for_same_seed_and_different_for_other_seed():
    questions, answers = _data({"number": 300, "percent": 100})
    a = build_devset(questions, answers, size=50, seed=7)
    b = build_devset(questions, answers, size=50, seed=7)
    c = build_devset(questions, answers, size=50, seed=8)
    assert [q["id"] for q in a] == [q["id"] for q in b]
    assert [q["id"] for q in a] != [q["id"] for q in c]


def test_take_subset_is_deterministic_prefix_of_shuffle():
    questions, answers = _data({"number": 100})
    dev = build_devset(questions, answers, size=40)
    s1 = take_subset(dev, 10, seed=3)
    assert len(s1) == 10 and [q["id"] for q in s1] == [q["id"] for q in take_subset(dev, 10, seed=3)]
```

- [ ] **Step 6: Viết `devset.py`**

```python
"""Bộ dev cố định từ train/ (SC-001): lấy mẫu phân tầng theo type, tỉ lệ theo phân bố thật để PA
ước lượng đúng điểm trên phân bố của BTC, tối thiểu min_per_type để type hiếm vẫn có mặt."""
from __future__ import annotations

import random
from collections import defaultdict


def build_devset(
    questions: list[dict], answers_by_id: dict, size: int = 200, seed: int = 42, min_per_type: int = 2
) -> list[dict]:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for q in sorted(questions, key=lambda q: q["id"]):
        by_type[answers_by_id[q["id"]]["type"]].append(q)

    total = sum(len(v) for v in by_type.values())
    quotas = {
        t: min(len(v), max(min_per_type, round(size * len(v) / total))) for t, v in by_type.items()
    }
    largest = max(quotas, key=quotas.get)
    quotas[largest] = min(len(by_type[largest]), quotas[largest] - (sum(quotas.values()) - size))

    rng = random.Random(seed)
    sample: list[dict] = []
    for type_name in sorted(by_type):
        items = list(by_type[type_name])
        rng.shuffle(items)
        sample.extend(items[: quotas[type_name]])
    return sorted(sample, key=lambda q: q["id"])


def take_subset(devset: list[dict], n: int, seed: int = 42) -> list[dict]:
    items = list(devset)
    random.Random(seed).shuffle(items)
    return sorted(items[:n], key=lambda q: q["id"])
```

- [ ] **Step 7: Test measure (resume + load + format)**

`tests/accuracy_boost/test_measure.py`:

```python
import json
from datetime import date
from pathlib import Path

from accuracy_boost.measure import collect_runs, format_curve, load_runs
from reasoning_agent.options import AgentOptions

DEV = [
    {"id": "q1", "business_id": "b", "question": "x", "as_of_date": "2026-01-01"},
    {"id": "q2", "business_id": "b", "question": "y", "as_of_date": "2026-01-02"},
]


def test_collect_runs_resumes_and_orders_by_run(tmp_path):
    out = tmp_path / "runs.jsonl"
    seen = []

    def run_fn(question, business_id, as_of_date, dataset_dir, options):
        seen.append((question, options.seed))
        return {"type": "number", "answer": options.seed}

    kwargs = dict(n_runs=3, sample_temperature=0.7, base_options=AgentOptions(seed=10), run_fn=run_fn)
    assert collect_runs(DEV, Path("."), out, **kwargs) == 6

    out.write_text("".join(out.read_text(encoding="utf-8").splitlines(True)[:4]), encoding="utf-8")
    seen.clear()
    assert collect_runs(DEV, Path("."), out, **kwargs) == 2
    assert len(seen) == 2

    runs = load_runs(out)
    assert [r["answer"] for r in runs["q1"]] == [10, 11, 12]
    assert set(runs) == {"q1", "q2"}


def test_exception_in_run_is_recorded_as_abstain_not_crash(tmp_path):
    out = tmp_path / "runs.jsonl"

    def run_fn(*args, **kwargs):
        raise RuntimeError("boom")

    collect_runs(DEV[:1], Path("."), out, n_runs=1, sample_temperature=0.7, base_options=AgentOptions(), run_fn=run_fn)
    row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert row["result"]["type"] == "abstain" and "boom" in row["result"]["error"]


def test_format_curve_is_markdown_table():
    text = format_curve([{"threshold": 0.6, "pa": 0.125, "correct": 3, "wrong": 1, "abstained": 4}])
    assert text.splitlines()[0].startswith("| threshold")
    assert "0.125" in text
```

- [ ] **Step 8: Viết `measure.py`**

```python
"""Thu kết quả N lần cho bộ dev (có resume) rồi tính PA theo ngưỡng — FR-002/FR-007.

Dùng:
  python -m accuracy_boost.measure collect --dataset-dir build_output/dev --out logs/base.jsonl [--limit 60]
  python -m accuracy_boost.measure report --runs logs/base.jsonl
Chỉ đọc train/ (FR-009)."""
from __future__ import annotations

import argparse
import json
import shutil
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Callable

from accuracy_boost.config import load_boost_config
from accuracy_boost.consensus import pa_curve
from accuracy_boost.devset import build_devset, take_subset
from accuracy_boost.gated import options_for_run
from data_loader.build_business_db import build_business
from reasoning_agent import answer_question
from reasoning_agent.options import AgentOptions

DEFAULT_TRAIN_DIR = Path("train")


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def prepare_dataset_dir(train_dir: Path, business_ids: list[str], dataset_dir: Path) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    for name in ("rulebook.md", "calendar.csv"):
        shutil.copy(train_dir / name, dataset_dir / name)
    for business_id in business_ids:
        if not (dataset_dir / f"{business_id}.duckdb").exists():
            build_business(train_dir / "data" / business_id, dataset_dir)


def _done_keys(path: Path) -> set[tuple[str, int]]:
    if not path.exists():
        return set()
    done = set()
    for row in _load_jsonl(path):
        done.add((row["id"], row["run"]))
    return done


def collect_runs(
    devset: list[dict],
    dataset_dir: Path,
    out_path: Path,
    *,
    n_runs: int,
    sample_temperature: float,
    base_options: AgentOptions,
    run_fn: Callable[..., dict] = answer_question,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = _done_keys(out_path)
    written = 0
    with out_path.open("a", encoding="utf-8") as out_file:
        for q in devset:
            for run_index in range(n_runs):
                if (q["id"], run_index) in done:
                    continue
                options = options_for_run(base_options, run_index, sample_temperature)
                started = time.monotonic()
                try:
                    result = run_fn(
                        q["question"], q["business_id"], date.fromisoformat(q["as_of_date"]), dataset_dir, options=options
                    )
                except FileNotFoundError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    result = {"type": "abstain", "error": str(exc)}
                row = {"id": q["id"], "run": run_index, "elapsed": round(time.monotonic() - started, 2), "result": result}
                out_file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                out_file.flush()
                written += 1
    return written


def load_runs(path: Path) -> dict[str, list[dict]]:
    by_id: dict[str, dict[int, dict]] = defaultdict(dict)
    for row in _load_jsonl(path):
        by_id[row["id"]][row["run"]] = row["result"]
    return {qid: [runs[i] for i in sorted(runs)] for qid, runs in by_id.items()}


def mean_elapsed(path: Path) -> float:
    rows = _load_jsonl(path)
    return sum(r["elapsed"] for r in rows) / len(rows) if rows else 0.0


def format_curve(rows: list[dict]) -> str:
    lines = ["| threshold | PA | correct | wrong | abstained |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['threshold']} | {r['pa']:.3f} | {r['correct']} | {r['wrong']} | {r['abstained']} |")
    return "\n".join(lines)


def _build_options(args) -> AgentOptions:
    return AgentOptions(seed=load_boost_config().base_seed, semantic_tools=args.semantic_tools)


def _cmd_collect(args) -> int:
    train_dir = Path(args.train_dir)
    questions = _load_jsonl(train_dir / "questions.jsonl")
    answers_by_id = {a["id"]: a for a in _load_jsonl(train_dir / "answers.jsonl")}
    devset = build_devset(questions, answers_by_id, size=args.size)
    if args.limit:
        devset = take_subset(devset, args.limit)
    prepare_dataset_dir(train_dir, sorted({q["business_id"] for q in devset}), Path(args.dataset_dir))
    cfg = load_boost_config()
    written = collect_runs(
        devset,
        Path(args.dataset_dir),
        Path(args.out),
        n_runs=args.n_runs or cfg.n_runs,
        sample_temperature=cfg.sample_temperature,
        base_options=_build_options(args),
    )
    print(f"đã ghi {written} lượt chạy vào {args.out}")
    return 0


def _cmd_report(args) -> int:
    train_dir = Path(args.train_dir)
    answers_by_id = {a["id"]: a for a in _load_jsonl(train_dir / "answers.jsonl")}
    runs = load_runs(Path(args.runs))
    thresholds = [float(t) for t in args.thresholds.split(",")]
    print("### Greedy (chỉ run 0, trả lời mọi câu)")
    greedy = {qid: results[:1] for qid, results in runs.items()}
    print(format_curve(pa_curve(greedy, answers_by_id, [0.0])))
    print("\n### Cổng tin cậy theo ngưỡng")
    print(format_curve(pa_curve(runs, answers_by_id, thresholds)))
    print(f"\nthời gian TB/lượt chạy: {mean_elapsed(Path(args.runs)):.1f}s, số câu: {len(runs)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="accuracy_boost.measure")
    sub = parser.add_subparsers(dest="cmd", required=True)

    collect = sub.add_parser("collect")
    collect.add_argument("--train-dir", default=str(DEFAULT_TRAIN_DIR))
    collect.add_argument("--dataset-dir", required=True)
    collect.add_argument("--out", required=True)
    collect.add_argument("--size", type=int, default=200)
    collect.add_argument("--limit", type=int, default=0)
    collect.add_argument("--n-runs", type=int, default=0)
    collect.add_argument("--semantic-tools", action="store_true")
    collect.set_defaults(func=_cmd_collect)

    report = sub.add_parser("report")
    report.add_argument("--train-dir", default=str(DEFAULT_TRAIN_DIR))
    report.add_argument("--runs", required=True)
    report.add_argument("--thresholds", default="0.3,0.6,1.0")
    report.set_defaults(func=_cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 9: Test runner bỏ dòng abstain**

`tests/answer_formatter/test_runner_abstain.py`:

```python
import json

from answer_formatter.runner import run_batch


def test_abstain_result_is_not_written_and_not_an_error(tmp_path):
    questions = tmp_path / "q.jsonl"
    questions.write_text(
        "".join(
            json.dumps({"id": i, "business_id": "b", "question": "x", "as_of_date": "2026-01-01"}) + "\n"
            for i in ("q1", "q2")
        ),
        encoding="utf-8",
    )

    calls = []

    def answer_fn(question, business_id, as_of_date, dataset_dir):
        calls.append(1)
        return {"type": "abstain"} if len(calls) == 1 else {"type": "number", "answer": 1}

    out = tmp_path / "submission.jsonl"
    summary = run_batch(questions, tmp_path, out, answer_fn=answer_fn)

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in rows] == ["q2"]
    assert summary.abstained == 1
    assert summary.errored == 0
```

(Lưu ý: `concurrency=1` mặc định nên thứ tự gọi tất định — câu `q1` abstain, `q2` được ghi.)

- [ ] **Step 10: Sửa `runner.py`**

(a) `BatchSummary` thêm cuối: `abstained: int = 0`.

(b) `_validate_contract`: đổi điều kiện thành
`if result["type"] not in ("unanswerable", "abstain") and "answer" not in result:`.

(c) Thay `_process_and_write` và vòng đếm:

```python
        def _process_and_write(q: dict) -> str:
            result, is_error = _answer_one(q, dataset_dir, answer_fn)
            if result.get("type") == "abstain":
                return "abstain"
            line = json.dumps({**result, "id": q["id"]}, ensure_ascii=False) + "\n"
            with write_lock:
                out_file.write(line)
                out_file.flush()
            return "error" if is_error else "ok"

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            statuses = list(pool.map(_process_and_write, remaining))
        errored = statuses.count("error")
        abstained = statuses.count("abstain")
```
(xoá biến `errored = 0` khởi tạo cũ) và `BatchSummary(..., abstained=abstained)`.
`normalize_answer` đã bỏ qua type lạ (trả nguyên) nên không cần sửa `normalize.py`.

- [ ] **Step 11: Chạy test**

Run: `pytest tests/accuracy_boost tests/answer_formatter -q`
Expected: toàn bộ PASS (kể cả test 005 cũ — nếu test cũ so sánh `BatchSummary` bằng bộ giá trị, sửa cho khớp field `abstained` mặc định 0).

- [ ] **Step 12: Commit**

```bash
git add src/accuracy_boost src/answer_formatter tests/accuracy_boost tests/answer_formatter
git commit -m "feat: add confidence-gated answering, dev-set measurement and abstain-aware batch runner"
```

---

### Task 4: `semantic_tools.py` — `aggregate` + `percent_change` (US2, FR-003/FR-004)

**Files:**
- Create: `src/reasoning_agent/semantic_tools.py`
- Modify: `src/reasoning_agent/agent.py` (nối dây khi `options.semantic_tools`)
- Test: `tests/reasoning_agent/test_semantic_tools.py`

**Interfaces:**
- Consumes: `ToolSpec` (react_loop), `schema` dict (`{"tables": [{"table_name", "columns": [{"name", "dtype", ...}]}]}`), DuckDB connection.
- Produces:
  - `build_semantic_tools(schema: dict, conn) -> dict[str, ToolSpec]` với 2 key `"aggregate"`, `"percent_change"`.
  - `SEMANTIC_TOOL_GUIDE: str` — đoạn hướng dẫn thêm vào system prompt.

- [ ] **Step 1: Viết test**

`tests/reasoning_agent/test_semantic_tools.py`:

```python
import duckdb
import pytest

from reasoning_agent.semantic_tools import build_semantic_tools

SCHEMA = {
    "tables": [
        {"table_name": "Don", "columns": [{"name": n, "dtype": d} for n, d in
                                            [("Ngày", "DATE"), ("Mã", "VARCHAR"), ("Tiền", "DOUBLE"), ("Trạng thái", "VARCHAR")]]},
        {"table_name": "Hang", "columns": [{"name": n, "dtype": d} for n, d in [("Mã", "VARCHAR"), ("SL", "BIGINT")]]},
    ]
}


@pytest.fixture
def tools():
    conn = duckdb.connect()
    conn.execute('CREATE TABLE Don ("Ngày" DATE, "Mã" VARCHAR, "Tiền" DOUBLE, "Trạng thái" VARCHAR)')
    conn.execute(
        "INSERT INTO Don VALUES ('2026-03-01','A',100,'ok'),('2026-03-02','B',50,'ok'),"
        "('2026-03-02','A',25,'Đã hủy'),('2026-04-01','A',10,'ok')"
    )
    conn.execute('CREATE TABLE Hang ("Mã" VARCHAR, "SL" BIGINT)')
    conn.execute("INSERT INTO Hang VALUES ('Y',10),('X',10),('Z',5)")
    return build_semantic_tools(SCHEMA, conn)


def agg(tools, **kw):
    return tools["aggregate"].handler(**kw)


def test_sum_in_date_range_with_exclusion_filter(tools):
    result = agg(
        tools, table="Don", agg="sum", value_column="Tiền", date_column="Ngày",
        start="2026-03-01", end="2026-03-31",
        filters=[{"column": "Trạng thái", "op": "not_in", "value": ["Đã hủy"]}],
    )
    assert result["rows"] == [[150.0]]
    assert "SUM" in result["sql"]


def test_count_distinct_and_plain_count(tools):
    assert agg(tools, table="Don", agg="count_distinct", value_column="Mã")["rows"] == [[2]]
    assert agg(tools, table="Don", agg="count")["rows"] == [[4]]


def test_group_by_top_n_with_tie_break_ascending(tools):
    result = agg(tools, table="Hang", agg="sum", value_column="SL", group_by=["Mã"], order="desc",
                 limit=2, tie_break_column="Mã")
    assert result["rows"] == [["X", 10], ["Y", 10]]


def test_unknown_names_list_valid_ones(tools):
    with pytest.raises(ValueError, match="Các table có"):
        agg(tools, table="Nope", agg="count")
    with pytest.raises(ValueError, match="Các cột có"):
        agg(tools, table="Don", agg="sum", value_column="Thành tiền")


def test_invalid_agg_op_and_missing_value_column(tools):
    with pytest.raises(ValueError):
        agg(tools, table="Don", agg="median", value_column="Tiền")
    with pytest.raises(ValueError):
        agg(tools, table="Don", agg="sum")
    with pytest.raises(ValueError):
        agg(tools, table="Don", agg="count", filters=[{"column": "Mã", "op": "regex", "value": "A"}])


def test_dates_without_date_column_rejected(tools):
    with pytest.raises(ValueError):
        agg(tools, table="Don", agg="count", start="2026-03-01")


def test_percent_change(tools):
    handler = tools["percent_change"].handler
    assert handler(current=90, previous=100) == {"percent_change": -10.0}
    assert handler(current=150, previous=100) == {"percent_change": 50.0}
    with pytest.raises(ValueError):
        handler(current=1, previous=0)
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/reasoning_agent/test_semantic_tools.py -v`
Expected: FAIL `ModuleNotFoundError: reasoning_agent.semantic_tools`.

- [ ] **Step 3: Viết `semantic_tools.py`**

```python
"""Semantic-layer tool (US2): tham số hoá các phép tổng hợp phổ biến, sinh SQL từ schema.json lúc
runtime. KHÔNG chứa tri thức ngành — trạng thái loại trừ/loại giao dịch do model chọn từ rulebook
(FR-004). Giá trị luôn bind bằng `?`, tên bảng/cột luôn kiểm với schema rồi mới quote."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from reasoning_agent.react_loop import ToolSpec

SEMANTIC_TOOL_GUIDE = """## Tool tổng hợp có sẵn (ưu tiên dùng thay cho viết SQL tự do)
- `aggregate`: sum/avg/min/max/count/count_distinct theo khoảng ngày [start, end] (gồm cả end),
  bộ lọc, nhóm theo, top-N (order + limit; `tie_break_column` xếp tăng dần khi bằng nhau). Tên
  bảng/cột đúng như danh sách trên; lỗi tên sẽ trả danh sách tên hợp lệ.
- `percent_change`: (current - previous) / |previous| * 100, làm tròn 2 chữ số.
Điều kiện lọc nghiệp vụ (trạng thái đơn loại trừ, loại giao dịch...) PHẢI chọn theo rulebook ở
trên. Chỉ dùng `run_sql` khi `aggregate` không diễn đạt được câu hỏi."""

_AGGS = {"sum", "avg", "min", "max", "count", "count_distinct"}
_COMPARE_OPS = {"=", "!=", ">", ">=", "<", "<=", "like"}
_LIST_OPS = {"in", "not_in"}


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def build_semantic_tools(schema: dict, conn) -> dict[str, ToolSpec]:
    columns_by_table = {t["table_name"]: [c["name"] for c in t["columns"]] for t in schema["tables"]}

    def check_table(table: str) -> str:
        if table not in columns_by_table:
            raise ValueError(f"table không tồn tại: {table!r}. Các table có: {sorted(columns_by_table)}")
        return _quote(table)

    def check_column(table: str, column: str) -> str:
        if column not in columns_by_table[table]:
            raise ValueError(f"cột {column!r} không có trong {table!r}. Các cột có: {columns_by_table[table]}")
        return _quote(column)

    def agg_expression(agg: str, value_column: str | None) -> str:
        if agg not in _AGGS:
            raise ValueError(f"agg không hợp lệ: {agg!r}, phải là 1 trong {sorted(_AGGS)}")
        if agg == "count":
            return "COUNT(*)" if value_column is None else f"COUNT({value_column})"
        if value_column is None:
            raise ValueError(f"agg={agg} cần value_column")
        if agg == "count_distinct":
            return f"COUNT(DISTINCT {value_column})"
        return f"{agg.upper()}({value_column})"

    def aggregate(
        table: str,
        agg: str,
        value_column: str | None = None,
        date_column: str | None = None,
        start: str | None = None,
        end: str | None = None,
        filters: list | None = None,
        group_by: list | None = None,
        order: str = "desc",
        limit: int | None = None,
        tie_break_column: str | None = None,
    ) -> dict:
        quoted_table = check_table(table)
        value = check_column(table, value_column) if value_column else None
        group_cols = [check_column(table, c) for c in (group_by or [])]

        where: list[str] = []
        params: list = []
        if (start or end) and not date_column:
            raise ValueError("start/end cần date_column")
        if date_column:
            quoted_date = check_column(table, date_column)
            if start:
                where.append(f"CAST({quoted_date} AS DATE) >= CAST(? AS DATE)")
                params.append(start)
            if end:
                where.append(f"CAST({quoted_date} AS DATE) <= CAST(? AS DATE)")
                params.append(end)
        for f in filters or []:
            column, op, operand = check_column(table, f["column"]), f["op"], f["value"]
            if op in _LIST_OPS:
                placeholders = ", ".join("?" for _ in operand)
                where.append(f"{column} {'IN' if op == 'in' else 'NOT IN'} ({placeholders})")
                params.extend(operand)
            elif op in _COMPARE_OPS:
                where.append(f"{column} {op.upper() if op == 'like' else op} ?")
                params.append(operand)
            else:
                raise ValueError(f"op không hợp lệ: {op!r}, phải là 1 trong {sorted(_COMPARE_OPS | _LIST_OPS)}")

        select = ", ".join(group_cols + [f"{agg_expression(agg, value)} AS value"])
        sql = f"SELECT {select} FROM {quoted_table}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        if group_cols:
            sql += " GROUP BY " + ", ".join(group_cols)
            if order not in ("asc", "desc"):
                raise ValueError("order phải là 'asc' hoặc 'desc'")
            sql += f" ORDER BY value {order.upper()}"
            if tie_break_column:
                sql += f", {check_column(table, tie_break_column)} ASC"
        if limit is not None:
            if int(limit) < 1:
                raise ValueError("limit phải >= 1")
            sql += f" LIMIT {int(limit)}"

        result = conn.execute(sql, params)
        columns = [d[0] for d in result.description]
        rows = [[_jsonable(v) for v in row] for row in result.fetchall()]
        return {"columns": columns, "rows": rows, "sql": sql, "params": params}

    def percent_change(current: float, previous: float) -> dict:
        if previous == 0:
            raise ValueError("previous = 0, không tính được phần trăm thay đổi")
        return {"percent_change": round((current - previous) / abs(previous) * 100, 2)}

    return {
        "aggregate": ToolSpec(
            schema={
                "name": "aggregate",
                "description": "Tổng hợp 1 bảng: sum/avg/min/max/count/count_distinct, khoảng ngày, bộ lọc, nhóm theo, top-N.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string"},
                        "agg": {"type": "string", "enum": sorted(_AGGS)},
                        "value_column": {"type": "string"},
                        "date_column": {"type": "string"},
                        "start": {"type": "string", "description": "yyyy-mm-dd, gồm cả ngày start"},
                        "end": {"type": "string", "description": "yyyy-mm-dd, gồm cả ngày end"},
                        "filters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "op": {"type": "string", "enum": sorted(_COMPARE_OPS | _LIST_OPS)},
                                    "value": {},
                                },
                                "required": ["column", "op", "value"],
                            },
                        },
                        "group_by": {"type": "array", "items": {"type": "string"}},
                        "order": {"type": "string", "enum": ["asc", "desc"]},
                        "limit": {"type": "integer"},
                        "tie_break_column": {"type": "string"},
                    },
                    "required": ["table", "agg"],
                },
            },
            handler=aggregate,
        ),
        "percent_change": ToolSpec(
            schema={
                "name": "percent_change",
                "description": "(current - previous) / |previous| * 100, làm tròn 2 chữ số.",
                "parameters": {
                    "type": "object",
                    "properties": {"current": {"type": "number"}, "previous": {"type": "number"}},
                    "required": ["current", "previous"],
                },
            },
            handler=percent_change,
        ),
    }
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `pytest tests/reasoning_agent/test_semantic_tools.py -v`
Expected: 7 PASS. Nếu `like` sinh `LIKE ?` sai (biểu thức `op.upper() if op == 'like' else op`), kiểm tra lại chuỗi SQL in ra.

- [ ] **Step 5: Test nối dây trong agent**

Thêm vào `tests/reasoning_agent/test_options_in_agent.py`:

```python
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
```

- [ ] **Step 6: Nối dây trong `agent.py`**

Sau khi tạo `extra` và trong khối `try` đã có `registry`:

```python
    extra = options.prompt_extra_fn(question) if options.prompt_extra_fn else ""
    if options.semantic_tools:
        extra = f"{extra}\n\n{SEMANTIC_TOOL_GUIDE}".strip()
    system_prompt = build_system_prompt(schema, rulebook_text, extra)
    ...
        if options.semantic_tools:
            registry.update(build_semantic_tools(schema, conn))
```
và import `from reasoning_agent.semantic_tools import SEMANTIC_TOOL_GUIDE, build_semantic_tools`.

- [ ] **Step 7: Chạy test + grep ràng buộc**

Run: `pytest tests/reasoning_agent -q --ignore=tests/reasoning_agent/test_baseline_golden.py`
Expected: PASS toàn bộ.
Run: `grep -rnE "business_id ?==|question_id ?==|biz_[0-9]+" src/ --include=*.py`
Expected: không có dòng nào (FR-008, SC-005).

- [ ] **Step 8: Commit**

```bash
git add src/reasoning_agent tests/reasoning_agent
git commit -m "feat: add semantic-layer aggregate and percent_change tools for the reasoning agent"
```

---

### Task 5: `fewshot.py` — pool few-shot từ `train/` (US3, FR-005/FR-009)

**Files:**
- Create: `src/accuracy_boost/fewshot.py`
- Modify: `src/accuracy_boost/measure.py` (cờ `--fewshot-k`)
- Test: `tests/accuracy_boost/test_fewshot.py`

**Interfaces:**
- Consumes: `AgentOptions.prompt_extra_fn` (Task 1).
- Produces:
  - `FewShotPool.from_train_dir(train_dir: Path) -> FewShotPool` (raise `ValueError` nếu thiếu `answers.jsonl` — chỉ `train/` có).
  - `FewShotPool.select(question: str, k: int, exclude_questions: frozenset[str] = frozenset()) -> list[dict]`
    (mỗi phần tử `{"question", "type"}`).
  - `FewShotPool.format_prompt(question, k, exclude_questions=frozenset()) -> str` (rỗng nếu không có ví dụ).

- [ ] **Step 1: Viết test**

`tests/accuracy_boost/test_fewshot.py`:

```python
import json

import pytest

from accuracy_boost.fewshot import FewShotPool


def _train_dir(tmp_path):
    rows = [
        ("q1", "Doanh thu tháng này là bao nhiêu?", "number"),
        ("q2", "Doanh thu tháng này so với tháng trước tăng giảm bao nhiêu %?", "percent"),
        ("q3", "Top 3 món bán chạy nhất tuần trước", "list"),
        ("q4", "Còn ai nợ tiền chưa trả?", "table"),
    ]
    (tmp_path / "questions.jsonl").write_text(
        "".join(json.dumps({"id": i, "business_id": "b", "question": q, "as_of_date": "2026-01-01"}, ensure_ascii=False) + "\n" for i, q, _ in rows),
        encoding="utf-8",
    )
    (tmp_path / "answers.jsonl").write_text(
        "".join(json.dumps({"id": i, "type": t, "answer": 1, "alias": []}) + "\n" for i, _, t in rows),
        encoding="utf-8",
    )
    return tmp_path


def test_selects_most_similar_ignoring_accents_and_case(tmp_path):
    pool = FewShotPool.from_train_dir(_train_dir(tmp_path))
    top = pool.select("doanh thu thang nay bao nhieu", k=1)
    assert top == [{"question": "Doanh thu tháng này là bao nhiêu?", "type": "number"}]


def test_excludes_identical_and_listed_questions(tmp_path):
    pool = FewShotPool.from_train_dir(_train_dir(tmp_path))
    question = "Doanh thu tháng này là bao nhiêu?"
    picked = pool.select(question, k=2, exclude_questions=frozenset({"Top 3 món bán chạy nhất tuần trước"}))
    texts = [p["question"] for p in picked]
    assert question not in texts
    assert "Top 3 món bán chạy nhất tuần trước" not in texts


def test_format_prompt_lists_type_only(tmp_path):
    pool = FewShotPool.from_train_dir(_train_dir(tmp_path))
    text = pool.format_prompt("Doanh thu tuần này?", k=2)
    assert "type=" in text and "đáp án" not in text.split("\n", 1)[1]
    assert FewShotPool([]).format_prompt("x", k=2) == ""


def test_requires_answers_file(tmp_path):
    (tmp_path / "questions.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="answers.jsonl"):
        FewShotPool.from_train_dir(tmp_path)
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/accuracy_boost/test_fewshot.py -v`
Expected: FAIL `ModuleNotFoundError: accuracy_boost.fewshot`.

- [ ] **Step 3: Viết `fewshot.py`**

```python
"""Few-shot từ train/ (US3). Chỉ truyền `type` của câu tương tự (train chỉ có đáp án, khác
business → giá trị đáp án dễ gây nhiễu). Độ giống = Jaccard token đã bỏ dấu. Chỉ train/ có
answers.jsonl nên from_train_dir tự chặn nguồn test (FR-009)."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def _tokens(text: str) -> frozenset[str]:
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return frozenset(re.findall(r"[a-z0-9]+", stripped))


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class FewShotPool:
    def __init__(self, items: list[dict]):
        self._items = [{**item, "tokens": _tokens(item["question"])} for item in items]

    @classmethod
    def from_train_dir(cls, train_dir: Path) -> "FewShotPool":
        answers_path = Path(train_dir) / "answers.jsonl"
        if not answers_path.exists():
            raise ValueError(f"Thiếu answers.jsonl trong {train_dir} — few-shot chỉ lấy từ train/")
        types = {a["id"]: a["type"] for a in _load_jsonl(answers_path)}
        items = [
            {"question": q["question"], "type": types[q["id"]]}
            for q in _load_jsonl(Path(train_dir) / "questions.jsonl")
            if q["id"] in types
        ]
        return cls(items)

    def select(self, question: str, k: int, exclude_questions: frozenset[str] = frozenset()) -> list[dict]:
        query = _tokens(question)
        scored = []
        for item in self._items:
            text = item["question"]
            if text == question or text in exclude_questions or not item["tokens"]:
                continue
            union = query | item["tokens"]
            scored.append((-len(query & item["tokens"]) / len(union), text, item["type"]))
        scored.sort()

        picked, seen = [], set()
        for _, text, type_name in scored:
            if text in seen:
                continue
            seen.add(text)
            picked.append({"question": text, "type": type_name})
            if len(picked) == k:
                break
        return picked

    def format_prompt(self, question: str, k: int, exclude_questions: frozenset[str] = frozenset()) -> str:
        examples = self.select(question, k, exclude_questions)
        if not examples:
            return ""
        lines = [f'- "{e["question"]}" → type={e["type"]}' for e in examples]
        return "## Câu hỏi tương tự trong bộ huấn luyện (chỉ để tham khảo kiểu đáp án)\n" + "\n".join(lines)
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `pytest tests/accuracy_boost/test_fewshot.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Thêm cờ `--fewshot-k` vào `measure.py`**

Trong `_build_options` đổi chữ ký thành `_build_options(args, train_dir, exclude_questions)`:

```python
def _build_options(args, train_dir: Path, exclude_questions: frozenset[str]) -> AgentOptions:
    prompt_extra_fn = None
    if args.fewshot_k > 0:
        pool = FewShotPool.from_train_dir(train_dir)
        prompt_extra_fn = lambda question: pool.format_prompt(question, args.fewshot_k, exclude_questions)
    return AgentOptions(
        seed=load_boost_config().base_seed, semantic_tools=args.semantic_tools, prompt_extra_fn=prompt_extra_fn
    )
```
Trong `_cmd_collect`: tính `exclude = frozenset(q["question"] for q in devset)` (trước khi `take_subset` thì dùng cả devset đầy đủ — lấy `full_dev` trước khi cắt), gọi `_build_options(args, train_dir, exclude)`. Thêm
`collect.add_argument("--fewshot-k", type=int, default=0)` và `from accuracy_boost.fewshot import FewShotPool`.

- [ ] **Step 6: Test chống rò rỉ ở CLI**

Thêm vào `tests/accuracy_boost/test_measure.py`:

```python
def test_collect_cli_excludes_dev_questions_from_fewshot(tmp_path, monkeypatch):
    from accuracy_boost import measure

    captured = {}

    def fake_collect(devset, dataset_dir, out_path, **kwargs):
        captured["extra"] = kwargs["base_options"].prompt_extra_fn(devset[0]["question"])
        return 0

    train = tmp_path / "train"
    train.mkdir()
    (train / "rulebook.md").write_text("r", encoding="utf-8")
    (train / "calendar.csv").write_text("c", encoding="utf-8")
    questions = [{"id": f"q{i}", "business_id": "b", "question": f"doanh thu thang {i}", "as_of_date": "2026-01-01"} for i in range(6)]
    (train / "questions.jsonl").write_text("".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8")
    (train / "answers.jsonl").write_text("".join(json.dumps({"id": q["id"], "type": "number", "answer": 1, "alias": []}) + "\n" for q in questions), encoding="utf-8")

    monkeypatch.setattr(measure, "collect_runs", fake_collect)
    monkeypatch.setattr(measure, "prepare_dataset_dir", lambda *a, **k: None)
    measure.main(["collect", "--train-dir", str(train), "--dataset-dir", str(tmp_path / "d"),
                  "--out", str(tmp_path / "o.jsonl"), "--size", "6", "--fewshot-k", "3"])
    assert captured["extra"] == ""
```
(Toàn bộ 6 câu thuộc devset nên tất cả bị loại trừ → prompt few-shot rỗng.)

- [ ] **Step 7: Chạy toàn bộ test + grep**

Run: `pytest tests -q --ignore=tests/reasoning_agent/test_baseline_golden.py --ignore=tests/data_loader`
Expected: PASS. (`tests/data_loader` golden chạy lâu/nhạy tải máy — bỏ qua ở đây, đã được verify ở C5.)
Run: `grep -rnE "public_test|private_test" src/accuracy_boost src/reasoning_agent/semantic_tools.py`
Expected: không có dòng nào (FR-009).

- [ ] **Step 8: Commit**

```bash
git add src/accuracy_boost tests/accuracy_boost
git commit -m "feat: add few-shot pool from train and --fewshot-k measurement flag"
```

---

### Task 6: Đo A/B trên bộ dev + quyết định mặc định (SC-001..SC-006) — vận hành, cần server thật

**Files:**
- Modify: `CHECKLIST-ZALO-DATAMATE-DUYET.md` (ghi kết quả, mục C8/C9)
- Modify: `TIEN_DO.md` (mục mới "ĐỢT 2026-11-xx — 007")
- Create: `docs/measure-007-results.md` (bảng số liệu thô; thư mục `docs/` đã có)
- Có thể modify: giá trị mặc định ở `src/accuracy_boost/config.py` / `AgentOptions` nếu số đo chứng minh có lợi.

**Interfaces:**
- Consumes: mọi thứ Task 1–5; model server OpenAI-compatible; train/ đầy đủ.
- Produces: bảng PA cho từng cấu hình + quyết định giữ/bỏ từng đòn bẩy.

- [ ] **Step 1: Kiểm môi trường**

Ollama đang chạy với tag `qwen2.5-7b-ctx12k` (đã tạo ở C7). Đặt env (PowerShell):

```powershell
$env:REASONING_AGENT_MODEL = "qwen2.5-7b-ctx12k"
$env:REASONING_AGENT_BASE_URL = "http://localhost:11434/v1"
```
Run: `curl http://localhost:11434/api/tags` → thấy `qwen2.5-7b-ctx12k`.

- [ ] **Step 2: Baseline + cổng tin cậy trên 60 câu (nhanh)**

```bash
python -m accuracy_boost.measure collect --dataset-dir build_output/dev007 --out logs/007_base.jsonl --limit 60 --n-runs 3
python -m accuracy_boost.measure report --runs logs/007_base.jsonl
```
Expected: lệnh `collect` chạy xong (resume được nếu ngắt — chạy lại cùng lệnh); `report` in 2 bảng.
Ghi vào `docs/measure-007-results.md`: PA greedy, PA từng ngưỡng, thời gian TB/lượt, số câu.
**Tiêu chí (SC-002):** PA tại ngưỡng được chọn ≥ 0 và ≥ PA greedy. Nếu mọi ngưỡng đều < 0 → ngưỡng
1.0 (đồng thuận tuyệt đối) là lựa chọn an toàn; nếu cả đó vẫn < 0, kết luận "đồng thuận không đủ" và
báo Khang (cân nhắc US1 AC3).

- [ ] **Step 3: A/B semantic-layer (cùng 60 câu)**

```bash
python -m accuracy_boost.measure collect --dataset-dir build_output/dev007 --out logs/007_semantic.jsonl --limit 60 --n-runs 3 --semantic-tools
python -m accuracy_boost.measure report --runs logs/007_semantic.jsonl
```
So bảng với Step 2 (cùng tập con vì `take_subset` có seed cố định). Ghi vào docs. **SC-003:** giữ
semantic-layer làm mặc định chỉ khi PA tăng; nếu không, ghi "không có lợi" và giữ tắt.

- [ ] **Step 4: A/B few-shot (cùng 60 câu, cấu hình tốt nhất từ Step 2–3)**

```bash
python -m accuracy_boost.measure collect --dataset-dir build_output/dev007 --out logs/007_fewshot.jsonl --limit 60 --n-runs 3 --fewshot-k 3 [--semantic-tools nếu Step 3 có lợi]
python -m accuracy_boost.measure report --runs logs/007_fewshot.jsonl
```
Ghi và quyết định giữ/bỏ như Step 3.

- [ ] **Step 5: Kiểm tính tất định (SC-006)**

Chạy lại đúng lệnh của cấu hình tốt nhất với `--out logs/007_rerun.jsonl`, so `report` hai lần:
`|ΔPA| ≤ 0.03`. Nếu lệch: ghi nhận nguyên nhân khả dĩ (batch/server) vào checklist.

- [ ] **Step 6: Mở rộng 200 câu cho cấu hình tốt nhất (SC-001)**

Bỏ `--limit`, chạy nền, ghi kết quả. Ghi thời gian TB/lượt để ngoại suy SC-004:
`thời gian ước tính private = 500 câu × N lượt × thời gian TB/lượt (máy dev) ÷ hệ số tăng tốc chưa biết` — chỉ ghi là cận trên.

- [ ] **Step 7: 14B-Q4 (cổng hỏi Khang)**

**DỪNG và hỏi Khang** trước khi tải GGUF Qwen 14B Q4 (~9GB, laptop/PC công ty: kiểm dung lượng ổ và
RAM). Sau khi Khang đồng ý, nạp model vào Ollama/llama.cpp (tag mới, `num_ctx 12288`), đổi 2 env var
`REASONING_AGENT_MODEL`/`REASONING_AGENT_BASE_URL`, chạy cùng cấu hình tốt nhất trên `--limit 50`
(`--out logs/007_14b.jsonl`), `report`, so với 7B cùng tập con. Ghi rõ: thời gian trên máy dev là cận
trên; ghi tên model, ngày phát hành, license (rule 8.2/8.9) để đưa vào README của solution.

- [ ] **Step 8: Ghi kết quả + chốt mặc định**

Cập nhật `docs/measure-007-results.md` (bảng đầy đủ), `CHECKLIST-ZALO-DATAMATE-DUYET.md` (C8: kết
quả + đòn bẩy nào giữ), `TIEN_DO.md` (mục 007). Nếu đòn bẩy nào có lợi: đổi giá trị mặc định tương
ứng (`threshold` ở `config.py`, `semantic_tools=True`, `--fewshot-k`) kèm test cập nhật.

- [ ] **Step 9: Commit**

```bash
git add docs/measure-007-results.md CHECKLIST-ZALO-DATAMATE-DUYET.md TIEN_DO.md src/accuracy_boost src/reasoning_agent
git commit -m "docs: record 007 A/B measurements and choose default accuracy levers"
```
