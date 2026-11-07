# Distill → Fine-tune (008) Tasks

> Thực thi theo `superpowers:subagent-driven-development`. Mỗi task kết thúc bằng deliverable test
> được độc lập. Đọc kèm `distill-finetune-plan.md` (kiến trúc + Global Constraints + reuse map).
> ⚠️ Chạy pytest có in tiếng Việt: `PYTHONIOENCODING=utf-8 python -m pytest ...` (bẫy cp1252).

---

### Task 1: Teacher config

**Files:**
- Create: `src/distill/__init__.py` (rỗng), `src/distill/teacher_config.py`
- Test: `tests/distill/__init__.py` (rỗng), `tests/distill/test_teacher_config.py`

**Interfaces:**
- Consumes: `reasoning_agent.config.AgentConfig(model, base_url, api_key)`
- Produces: `load_teacher_config() -> AgentConfig` (đọc `TEACHER_MODEL`/`TEACHER_BASE_URL`/`TEACHER_API_KEY`)

- [ ] **Step 1: Write failing test**

```python
# tests/distill/test_teacher_config.py
import pytest
from distill.teacher_config import load_teacher_config

def test_loads_from_env(monkeypatch):
    monkeypatch.setenv("TEACHER_MODEL", "llama-3.3-70b")
    monkeypatch.setenv("TEACHER_BASE_URL", "https://gw.free/v1/")
    monkeypatch.setenv("TEACHER_API_KEY", "k")
    cfg = load_teacher_config()
    assert (cfg.model, cfg.base_url, cfg.api_key) == ("llama-3.3-70b", "https://gw.free/v1", "k")

def test_missing_model_raises(monkeypatch):
    monkeypatch.delenv("TEACHER_MODEL", raising=False)
    monkeypatch.setenv("TEACHER_BASE_URL", "https://gw.free/v1")
    with pytest.raises(ValueError, match="TEACHER_MODEL"):
        load_teacher_config()
```

- [ ] **Step 2: Run → verify FAIL** (`ModuleNotFoundError: distill`)

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/distill/test_teacher_config.py -v`

- [ ] **Step 3: Implement**

```python
# src/distill/teacher_config.py
from __future__ import annotations
import os
from reasoning_agent.config import AgentConfig

def load_teacher_config() -> AgentConfig:
    model = os.environ.get("TEACHER_MODEL", "").strip()
    base_url = os.environ.get("TEACHER_BASE_URL", "").strip()
    if not model:
        raise ValueError("Thiếu biến môi trường TEACHER_MODEL")
    if not base_url:
        raise ValueError("Thiếu biến môi trường TEACHER_BASE_URL")
    return AgentConfig(model=model, base_url=base_url.rstrip("/"),
                       api_key=os.environ.get("TEACHER_API_KEY", ""))
```

- [ ] **Step 4: Run → verify PASS**
- [ ] **Step 5: Commit** — `git add src/distill tests/distill && git commit -m "feat: add teacher config loader for distillation (FR-011)"`

---

### Task 2: Trace generator (ghi messages, không sửa lõi 004)

**Files:**
- Create: `src/distill/trace_generator.py`
- Test: `tests/distill/test_trace_generator.py`

**Interfaces:**
- Consumes: `load_calendar`, `build_date_tool_registry`, `build_system_prompt`,
  `build_schema_tools`+`load_schema`, `build_sql_tool`, `run_react_loop`, `call_chat_completion`,
  `AgentConfig`. Test fixture `build_real_business` (copy từ `tests/reasoning_agent/conftest.py`).
- Produces: `@dataclass TraceResult(result: dict, messages: list[dict])`;
  `generate_trace(question, business_id, as_of_date, dataset_dir, teacher_config, temperature=0.0, seed=42, chat_completion_fn=call_chat_completion) -> TraceResult`

- [ ] **Step 1: Thêm fixture** — copy `build_real_business` + `TRAIN_DIR`/`PROJECT_ROOT` vào
  `tests/distill/conftest.py` (y hệt `tests/reasoning_agent/conftest.py`; reuse data thật train/).

- [ ] **Step 2: Write failing test**

```python
# tests/distill/test_trace_generator.py
import json
from datetime import date
from reasoning_agent.config import AgentConfig
from distill.trace_generator import generate_trace
from .conftest import build_real_business

_SQL = ('SELECT COUNT(DISTINCT "Mã đơn hàng") FROM DonHang_ChiTiet '
        "WHERE \"Ngày đặt hàng\" = DATE '2026-03-28' "
        "AND \"Trạng thái đơn hàng\" NOT IN ('Đã hủy', 'Đã hoàn hàng')")

def _fake_teacher():
    n = {"i": 0}
    def fn(config, messages, tools, timeout, **kw):
        n["i"] += 1
        if n["i"] == 1:
            return {"content": None, "tool_calls":
                    [{"id": "1", "name": "run_sql", "arguments": json.dumps({"query": _SQL})}]}
        return {"content": None, "tool_calls":
                [{"id": "2", "name": "submit_answer",
                  "arguments": json.dumps({"type": "number", "answer_json": "73"})}]}
    return fn

def test_generate_trace_captures_full_messages(tmp_path):
    build_real_business(tmp_path, "biz_102")
    tc = AgentConfig(model="t", base_url="http://x", api_key="")
    tr = generate_trace("Hôm qua bán mấy đơn?", "biz_102", date(2026, 3, 29), tmp_path, tc,
                        chat_completion_fn=_fake_teacher())
    assert tr.result == {"type": "number", "answer": 73}
    assert any(m.get("role") == "tool" for m in tr.messages)            # có kết quả run_sql
    last = tr.messages[-1]
    assert last["role"] == "assistant"
    assert last["tool_calls"][0]["function"]["name"] == "submit_answer"  # trace kết ở submit
```

- [ ] **Step 3: Run → verify FAIL**
- [ ] **Step 4: Implement** (mirror `agent.answer_question`, thêm `recording_chat_fn`)

```python
# src/distill/trace_generator.py
from __future__ import annotations
import copy
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable
import duckdb
from date_resolver import load_calendar
from reasoning_agent.config import AgentConfig
from reasoning_agent.date_tools import build_date_tool_registry
from reasoning_agent.llm_client import call_chat_completion
from reasoning_agent.prompt import build_system_prompt
from reasoning_agent.react_loop import run_react_loop
from reasoning_agent.schema_tools import build_schema_tools, load_schema
from reasoning_agent.sql_tool import build_sql_tool

@dataclass
class TraceResult:
    result: dict
    messages: list[dict]

def generate_trace(question: str, business_id: str, as_of_date: date, dataset_dir: Path,
                   teacher_config: AgentConfig, temperature: float = 0.0, seed: int = 42,
                   chat_completion_fn: Callable = call_chat_completion) -> TraceResult:
    rulebook_text = (dataset_dir / "rulebook.md").read_text(encoding="utf-8")
    calendar_index = load_calendar(str(dataset_dir / "calendar.csv"))
    schema = load_schema(dataset_dir, business_id)
    system_prompt = build_system_prompt(schema, rulebook_text, "")
    conn = duckdb.connect(str(dataset_dir / f"{business_id}.duckdb"), read_only=True)
    try:
        registry = {**build_date_tool_registry(calendar_index, as_of_date),
                    **build_schema_tools(schema), "run_sql": build_sql_tool(conn)}
        captured: dict = {}
        def recording_chat_fn(messages, tools, timeout):
            captured["messages"] = messages  # cùng object list mà run_react_loop bồi đắp
            return chat_completion_fn(teacher_config, messages, tools, timeout,
                                      temperature=temperature, seed=seed)
        result = run_react_loop(recording_chat_fn, system_prompt, question, registry)
        return TraceResult(result=result, messages=copy.deepcopy(captured.get("messages", [])))
    finally:
        conn.close()
```

- [ ] **Step 5: Run → verify PASS**
- [ ] **Step 6: Commit** — `git commit -am "feat: add trace generator capturing ReAct messages (FR-001)"`

---

### Task 3: Verified collection (rejection sampling)

**Files:**
- Create: `src/distill/collect.py`
- Test: `tests/distill/test_collect.py`

**Interfaces:**
- Consumes: `eval_harness.matchers.is_correct(truth_type, predicted, truth_answer, alias)`,
  `generate_trace`, `TraceResult`.
- Produces: `collect_verified_trace(question, business_id, as_of_date, dataset_dir, teacher_config,
  truth_type, truth_answer, alias, max_attempts=3, base_seed=42, generate_fn=generate_trace,
  chat_completion_fn=call_chat_completion) -> TraceResult | None`

- [ ] **Step 1: Write failing test** (inject `generate_fn` giả — không cần model/DuckDB)

```python
# tests/distill/test_collect.py
from datetime import date
from reasoning_agent.config import AgentConfig
from distill.trace_generator import TraceResult
from distill.collect import collect_verified_trace

_TC = AgentConfig(model="t", base_url="http://x", api_key="")

def test_returns_on_first_verified_attempt():
    calls = {"n": 0}
    def gen(*a, **k):
        calls["n"] += 1
        val = 0 if calls["n"] == 1 else 73          # sai lần 1, đúng lần 2
        return TraceResult(result={"type": "number", "answer": val}, messages=[{"x": calls["n"]}])
    tr = collect_verified_trace("q", "b", date(2026, 3, 29), None, _TC,
                                "number", 73, [], max_attempts=3, generate_fn=gen)
    assert calls["n"] == 2 and tr.result["answer"] == 73

def test_returns_none_when_never_verified():
    def gen(*a, **k):
        return TraceResult(result={"type": "number", "answer": 0}, messages=[])
    assert collect_verified_trace("q", "b", date(2026, 3, 29), None, _TC,
                                  "number", 73, [], max_attempts=3, generate_fn=gen) is None
```

- [ ] **Step 2: Run → verify FAIL**
- [ ] **Step 3: Implement**

```python
# src/distill/collect.py
from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Callable
from eval_harness.matchers import is_correct
from reasoning_agent.config import AgentConfig
from reasoning_agent.llm_client import call_chat_completion
from distill.trace_generator import TraceResult, generate_trace

def collect_verified_trace(question: str, business_id: str, as_of_date: date, dataset_dir: Path,
                           teacher_config: AgentConfig, truth_type: str, truth_answer, alias: list,
                           max_attempts: int = 3, base_seed: int = 42,
                           generate_fn: Callable = generate_trace,
                           chat_completion_fn: Callable = call_chat_completion) -> TraceResult | None:
    for i in range(max_attempts):
        trace = generate_fn(question, business_id, as_of_date, dataset_dir, teacher_config,
                            temperature=0.0 if i == 0 else 0.7, seed=base_seed + i,
                            chat_completion_fn=chat_completion_fn)
        if is_correct(truth_type, trace.result, truth_answer, alias):
            return trace
    return None
```

- [ ] **Step 4: Run → verify PASS**
- [ ] **Step 5: Commit** — `git commit -am "feat: add rejection-sampling trace collection (FR-002/FR-003)"`

---

### Task 4: Generation CLI (cache/resume, loại DevSet)

**Files:**
- Create: `src/distill/cli.py`
- Test: `tests/distill/test_cli.py`

**Interfaces:**
- Consumes: `collect_verified_trace`, `accuracy_boost.devset.build_devset`.
- Produces: `run_generation(questions, answers_by_id, dataset_dir, out_path, devset_ids,
  collect_fn=collect_verified_trace, max_attempts=3) -> dict` (counts) — ghi append JSONL mỗi câu
  `{"id","business_id","status":"verified"|"failed","messages":[...]|null}`; bỏ qua id đã có trong
  `out_path` (resume) và id thuộc `devset_ids`. `main()` tính `devset_ids` bằng `build_devset`.

- [ ] **Step 1: Write failing test** (inject `collect_fn` giả; `devset_ids` truyền tay)

```python
# tests/distill/test_cli.py
import json
from datetime import date
from distill.trace_generator import TraceResult
from distill.cli import run_generation

def _collect_ok(q, b, d, dd, tc, tt, ta, al, **k):
    return TraceResult(result={"type": tt, "answer": ta}, messages=[{"role": "user"}])

def test_excludes_devset_and_resumes(tmp_path):
    qs = [{"id": "a", "business_id": "b1", "question": "?", "as_of_date": "2026-03-29"},
          {"id": "dev", "business_id": "b1", "question": "?", "as_of_date": "2026-03-29"},
          {"id": "c", "business_id": "b1", "question": "?", "as_of_date": "2026-03-29"}]
    ans = {q["id"]: {"type": "number", "answer": 1, "alias": []} for q in qs}
    out = tmp_path / "traces.jsonl"
    c1 = run_generation(qs, ans, tmp_path, out, devset_ids={"dev"}, collect_fn=_collect_ok)
    ids = [json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines()]
    assert ids == ["a", "c"] and c1["verified"] == 2        # "dev" bị loại
    # resume: chạy lại không thêm dòng
    run_generation(qs, ans, tmp_path, out, devset_ids={"dev"}, collect_fn=_collect_ok)
    ids2 = [json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines()]
    assert ids2 == ["a", "c"]
```

- [ ] **Step 2: Run → verify FAIL**
- [ ] **Step 3: Implement** (`run_generation` + `main`; `main` chỉ parse args + build devset + đọc
  train, không logic test-được riêng — fold vào task này)

```python
# src/distill/cli.py
from __future__ import annotations
import argparse, json, os, time
from datetime import date
from pathlib import Path
from typing import Callable
from accuracy_boost.devset import build_devset
from distill.collect import collect_verified_trace
from distill.teacher_config import load_teacher_config

def _done_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    return {json.loads(l)["id"] for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()}

def run_generation(questions, answers_by_id, dataset_dir, out_path, devset_ids,
                   collect_fn: Callable = collect_verified_trace, max_attempts: int = 3,
                   teacher_config=None) -> dict:
    out_path = Path(out_path)
    done = _done_ids(out_path)
    counts = {"verified": 0, "failed": 0, "skipped": 0}
    with out_path.open("a", encoding="utf-8") as f:
        for q in questions:
            qid = q["id"]
            if qid in devset_ids or qid in done:
                counts["skipped"] += 1
                continue
            g = answers_by_id[qid]
            trace = collect_fn(q["question"], q["business_id"], date.fromisoformat(q["as_of_date"]),
                               dataset_dir, teacher_config, g["type"], g.get("answer"),
                               g.get("alias", []), max_attempts=max_attempts)
            rec = {"id": qid, "business_id": q["business_id"],
                   "status": "verified" if trace else "failed",
                   "messages": trace.messages if trace else None}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            counts["verified" if trace else "failed"] += 1
    return counts

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--questions", required=True); p.add_argument("--answers", required=True)
    p.add_argument("--dataset-dir", required=True); p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--max-attempts", type=int, default=int(os.environ.get("DISTILL_MAX_ATTEMPTS", "3")))
    p.add_argument("--devset-size", type=int, default=200)
    a = p.parse_args()
    questions = [json.loads(l) for l in Path(a.questions).read_text(encoding="utf-8").splitlines() if l.strip()]
    answers = {json.loads(l)["id"]: json.loads(l)
               for l in Path(a.answers).read_text(encoding="utf-8").splitlines() if l.strip()}
    devset_ids = {q["id"] for q in build_devset(questions, answers, size=a.devset_size)}
    if a.limit:
        questions = questions[: a.limit]
    counts = run_generation(questions, answers, Path(a.dataset_dir), Path(a.out), devset_ids,
                            max_attempts=a.max_attempts, teacher_config=load_teacher_config())
    print("counts:", counts)

if __name__ == "__main__":
    main()
```
> Ghi chú reuse: backoff rate-limit — `collect_verified_trace` gọi `generate_trace` → `call_chat_completion`
> raise `LLMClientError` khi timeout/HTTP lỗi; vòng `for i in range(max_attempts)` đã nuốt lần lỗi
> (coi như attempt hỏng). Nếu cổng free trả 429 nhiều, thêm `time.sleep` backoff TRONG `main` giữa câu
> (đã import `time`) — giữ tối thiểu, chỉ thêm khi đo thấy bị chặn (YAGNI).

- [ ] **Step 4: Run → verify PASS**
- [ ] **Step 5: Commit** — `git commit -am "feat: add distillation generation CLI with resume + devset exclusion (FR-004)"`

---

### Task 5: SFT dataset builder

**Files:**
- Create: `src/distill/dataset_builder.py`
- Test: `tests/distill/test_dataset_builder.py`

**Interfaces:**
- Produces: `build_sft_records(trace_records, devset_ids) -> list[dict]` — lọc `status=="verified"`,
  loại `devset_ids` (double-guard), dedupe theo hash `messages`, trả `{"messages":[...], "meta":{"id","business_id"}}`.
  `write_sft(records, out_path)` ghi JSONL.

- [ ] **Step 1: Write failing test**

```python
# tests/distill/test_dataset_builder.py
from distill.dataset_builder import build_sft_records

def test_filters_dedupes_and_excludes_devset():
    msg = [{"role": "user", "content": "x"}]
    recs = [
        {"id": "a", "business_id": "b1", "status": "verified", "messages": msg},
        {"id": "a2", "business_id": "b1", "status": "verified", "messages": msg},   # trùng nội dung
        {"id": "dev", "business_id": "b1", "status": "verified", "messages": [{"role": "user", "content": "y"}]},
        {"id": "f", "business_id": "b1", "status": "failed", "messages": None},
    ]
    out = build_sft_records(recs, devset_ids={"dev"})
    assert len(out) == 1                       # dedupe trùng + loại dev + bỏ failed
    assert out[0]["messages"] == msg and out[0]["meta"]["id"] == "a"
```

- [ ] **Step 2: Run → verify FAIL**
- [ ] **Step 3: Implement**

```python
# src/distill/dataset_builder.py
from __future__ import annotations
import json
from pathlib import Path

def build_sft_records(trace_records, devset_ids) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in trace_records:
        if r.get("status") != "verified" or r["id"] in devset_ids or not r.get("messages"):
            continue
        key = json.dumps(r["messages"], ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append({"messages": r["messages"], "meta": {"id": r["id"], "business_id": r["business_id"]}})
    return out

def write_sft(records, out_path) -> None:
    Path(out_path).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")

def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--traces", required=True); p.add_argument("--questions", required=True)
    p.add_argument("--answers", required=True); p.add_argument("--out", required=True)
    p.add_argument("--devset-size", type=int, default=200)
    a = p.parse_args()
    from accuracy_boost.devset import build_devset
    recs = [json.loads(l) for l in Path(a.traces).read_text(encoding="utf-8").splitlines() if l.strip()]
    questions = [json.loads(l) for l in Path(a.questions).read_text(encoding="utf-8").splitlines() if l.strip()]
    answers = {json.loads(l)["id"]: json.loads(l)
               for l in Path(a.answers).read_text(encoding="utf-8").splitlines() if l.strip()}
    devset_ids = {q["id"] for q in build_devset(questions, answers, size=a.devset_size)}
    sft = build_sft_records(recs, devset_ids)
    write_sft(sft, a.out)
    print(f"SFT records: {len(sft)}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run → verify PASS**
- [ ] **Step 5: Commit** — `git commit -am "feat: add SFT dataset builder with dedupe + devset guard (FR-004)"`

---

### Task 6: QLoRA training script (Kaggle) — KHÔNG pytest

**Files:**
- Create: `scripts/kaggle_qlora.py`, `specs/008-distill-finetune/KAGGLE.md`

**Lưu ý:** deps (`torch`, `unsloth`, `trl`, `peft`, `bitsandbytes`) **chỉ cài trên Kaggle**, KHÔNG
thêm vào `requirements.txt`. Task này deliverable = script chạy được + smoke run; "test" = smoke 20 mẫu.

- [ ] **Step 1: Viết `scripts/kaggle_qlora.py`** — QLoRA Qwen2.5-Coder-7B qua Unsloth, nạp SFT JSONL
  (mỗi dòng `{"messages":[...]}`), format bằng `tokenizer.apply_chat_template(..., tools=...)`,
  `train_on_responses_only` (chỉ học assistant-turn), lưu LoRA adapter. Có cờ `--smoke` (20 mẫu, 1 step).

```python
# scripts/kaggle_qlora.py  (chạy trên Kaggle GPU; xem KAGGLE.md)
import argparse, json
from unsloth import FastLanguageModel
from unsloth.chat_templates import train_on_responses_only
from trl import SFTTrainer, SFTConfig
from datasets import Dataset

def load_rows(path, limit=0):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    return rows[:limit] if limit else rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--out", default="adapter")
    ap.add_argument("--model", default="unsloth/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--epochs", type=float, default=1.0); ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    model, tok = FastLanguageModel.from_pretrained(a.model, max_seq_length=8192,
                                                   load_in_4bit=True, dtype=None)
    model = FastLanguageModel.get_peft_model(model, r=16, lora_alpha=16, random_state=42,
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"])
    rows = load_rows(a.data, limit=20 if a.smoke else 0)
    def fmt(r):  # messages -> text theo chat template (có tools)
        return {"text": tok.apply_chat_template(r["messages"], tokenize=False)}
    ds = Dataset.from_list([fmt(r) for r in rows])
    trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=ds,
        args=SFTConfig(output_dir=a.out, per_device_train_batch_size=1, gradient_accumulation_steps=4,
            warmup_steps=5, max_steps=1 if a.smoke else -1, num_train_epochs=a.epochs,
            learning_rate=2e-4, seed=42, logging_steps=1, optim="adamw_8bit"))
    trainer = train_on_responses_only(trainer,
        instruction_part="<|im_start|>user\n", response_part="<|im_start|>assistant\n")
    trainer.train()
    model.save_pretrained(a.out); tok.save_pretrained(a.out)
    print("saved adapter ->", a.out)

if __name__ == "__main__":
    main()
```
> ⚠️ Chốt lúc chạy smoke: Qwen2.5 chat template có render đúng `tool_calls`/`tool` role không — nếu
> template bản Unsloth khác, chỉnh `apply_chat_template`/`response_part` cho khớp. Đây là điểm phải
> xác nhận bằng smoke run, không phỏng đoán.

- [ ] **Step 2: Viết `KAGGLE.md`** — gồm: (a) cell cài deps Kaggle; (b) upload SFT JSONL; (c) lệnh
  `python kaggle_qlora.py --data sft.jsonl --smoke` (smoke) rồi full; (d) **model card tuân thủ**:
  base `Qwen2.5-Coder-7B-Instruct`, Apache-2.0, phát hành 09/2024 (< 26/10/2026), LoRA r=16 tính
  vào tổng ≤15B (rule 8.2); (e) cách serve adapter qua vLLM (OpenAI endpoint) để `reasoning_agent`
  dùng bằng `REASONING_AGENT_MODEL`/`BASE_URL` (FR-006); (f) nhắc gửi dataset + script cho
  `aichallenge@zalo.me` verify (rule 8.9.1/8.9.3).

- [ ] **Step 3: Smoke** (trên Kaggle, không ở máy dev) — `--smoke` chạy hết 1 step, lưu adapter,
  không lỗi template. Ghi kết quả smoke vào `KAGGLE.md`.
- [ ] **Step 4: Commit** — `git commit -am "feat: add Kaggle QLoRA training script + runbook (FR-005, US2)"`

---

### Task 7: Error analysis + quy trình đo PA trước/sau

**Files:**
- Create: `src/distill/error_analysis.py`
- Test: `tests/distill/test_error_analysis.py`
- Doc: thêm mục "Đo PA 008" vào `docs/measure-007-results.md` (hoặc file mới `docs/measure-008-results.md`)

**Interfaces:**
- Consumes: `eval_harness.matchers.is_correct`.
- Produces: `classify_outcomes(predictions, answers_by_id) -> dict[str,int]` với nhãn
  `correct` / `wrong_VALUE` / `wrong_TYPE` / `abstain_model` / `abstain_budget` / `wrong_should_abstain`.
  `predictions`: list `{"id", "result": {"type","answer"?,"reason"?}}`.

- [ ] **Step 1: Write failing test**

```python
# tests/distill/test_error_analysis.py
from distill.error_analysis import classify_outcomes

def test_classifies_core_buckets():
    gold = {"1": {"type": "number", "answer": 10, "alias": []},
            "2": {"type": "number", "answer": 10, "alias": []},
            "3": {"type": "unanswerable", "answer": None, "alias": []}}
    preds = [
        {"id": "1", "result": {"type": "number", "answer": 10}},                 # correct
        {"id": "2", "result": {"type": "number", "answer": 99}},                 # wrong_VALUE
        {"id": "3", "result": {"type": "number", "answer": 1}},                  # wrong_should_abstain
    ]
    out = classify_outcomes(preds, gold)
    assert out["correct"] == 1 and out["wrong_VALUE"] == 1 and out["wrong_should_abstain"] == 1
```

- [ ] **Step 2: Run → verify FAIL**
- [ ] **Step 3: Implement**

```python
# src/distill/error_analysis.py
from __future__ import annotations
from collections import Counter
from eval_harness.matchers import is_correct
from reasoning_agent.react_loop import BUDGET_EXHAUSTED_REASON

def classify_outcomes(predictions, answers_by_id) -> dict[str, int]:
    c: Counter = Counter()
    for p in predictions:
        g = answers_by_id[p["id"]]; res = p["result"]; pt = res.get("type")
        if is_correct(g["type"], res, g.get("answer"), g.get("alias", [])):
            c["correct"] += 1
        elif pt == "unanswerable":
            c["abstain_budget" if res.get("reason") == BUDGET_EXHAUSTED_REASON else "abstain_model"] += 1
        elif g["type"] == "unanswerable":
            c["wrong_should_abstain"] += 1
        elif pt != g["type"]:
            c["wrong_TYPE"] += 1
        else:
            c["wrong_VALUE"] += 1
    return dict(c)
```

- [ ] **Step 4: Run → verify PASS**
- [ ] **Step 5: Commit** — `git commit -am "feat: add outcome classifier for before/after error analysis (SC-003)"`

- [ ] **Step 6: Quy trình đo PA (chạy trên Kaggle T4, không code mới)** — viết vào
  `docs/measure-008-results.md`:
  1. Serve base Coder-7B và fine-tuned (base+adapter) qua vLLM OpenAI endpoint.
  2. Với mỗi model: `REASONING_AGENT_MODEL=<model> REASONING_AGENT_BASE_URL=<vllm> PYTHONIOENCODING=utf-8
     python -m accuracy_boost.measure collect --dataset-dir <built train> --out runs_<model>.jsonl --limit 200`
     rồi `... report --runs runs_<model>.jsonl` (reuse 007 — PA trên DevSet).
  3. Chạy `classify_outcomes` trên cả 2 → bảng phân loại lỗi; kỳ vọng **wrong_VALUE giảm** (SC-003),
     **PA(tuned) > PA(base)** (SC-002). Nếu không, ghi "không có lợi" + lý do vào checklist C8 (SDD Điều 2).

---

## Sau khi xong tất cả

- [ ] Cập nhật `CHECKLIST-ZALO-DATAMATE-DUYET.md` (C8) + `TIEN_DO.md` với số PA thật.
- [ ] `grep` nguồn sạch (SC-005): `business_id ==`/`question_id ==`/`qwen` trong `src/distill/`.
- [ ] Đóng gói cho 006: adapter + `scripts/kaggle_qlora.py` + dataset verified + `KAGGLE.md` (rule 8.9.3).
