# Distill → Fine-tune (008) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans để thực thi plan này theo từng task. Steps chi tiết
> dùng checkbox (`- [ ]`): `specs/008-distill-finetune/distill-finetune-tasks.md`.

**Goal:** Sinh dataset SQL-trace đã verify từ `train/` (teacher LLM lớn qua cổng API free) rồi
QLoRA fine-tune student ≤15B để nâng PA, đánh thẳng vào lỗi 42% wrong_VALUE đã chẩn đoán.

**Architecture:** Generator **tái dùng nguyên bộ máy agent của 004** — chạy teacher qua
`run_react_loop` với tool thật (run_sql execute trên DuckDB ngay trong vòng), nên verify "SQL →
đáp án" là nội tại: trace được GIỮ chỉ khi đáp án cuối khớp `train/answers.jsonl` qua
`eval_harness.is_correct`. Trace đúng (mảng `messages` OpenAI tool-calling) → SFT dataset →
QLoRA Coder-7B trên Kaggle free → student chạy trong Docker qua env (không sửa lõi 004).

**Tech Stack:** Python 3.11, DuckDB, pytest, stdlib (package `src/distill/` không thêm dependency).
Training TÁCH RIÊNG trên Kaggle (`scripts/kaggle_qlora.py`): torch/unsloth/peft/trl — **chỉ cài
trên Kaggle, KHÔNG thêm vào `requirements.txt`** (Điều 1/8 + CLAUDE.md: không cài lib nặng ở máy dev).

**Spec:** `specs/008-distill-finetune/spec.md`

## Global Constraints

- Teacher (API ngoài) CHỈ dùng lúc sinh data (offline); MUST NOT là dependency lúc inference/Docker
  (FR-011, rule 8.3).
- Chỉ dùng `train/`; MUST NOT đụng `public_test`/`private_test` cho data/verify/tuning (FR-004, rule 8.9.2).
- Loại mọi câu thuộc **DevSet** (build bằng `accuracy_boost.devset.build_devset`, size=200, seed=42)
  khỏi dataset train (FR-004, chống rò rỉ khi đo PA).
- Tổng tham số inference ≤15B; base public trước 26/10/2026, license OSI; khai báo README (FR-009,
  rule 8.2). Student mặc định **Qwen2.5-Coder-7B-Instruct** (Apache-2.0, 09/2024 — đã verify).
- KHÔNG logic rẽ nhánh theo `business_id`/`question_id`/tên cột trong generator lẫn data (FR-008, Điều 10).
- Model/endpoint teacher qua env `TEACHER_MODEL`/`TEACHER_BASE_URL`/`TEACHER_API_KEY`; student qua
  `REASONING_AGENT_MODEL`/`REASONING_AGENT_BASE_URL` (reuse, FR-006). Không hard-code tên model (SC-005).
- Student sau train: temp 0 + seed cố định để re-run |ΔPA| ≤ 0.03 (FR-010, rule 8.8).
- Reuse, không viết lại: `eval_harness.is_correct` (verify), `reasoning_agent.*` builders
  (`answer_question` wiring), `accuracy_boost.devset`/`measure` (đo PA).
- File Python `snake_case`, tách khi > ~250 dòng (Điều 5). Commit Conventional Commits tiếng Anh;
  KHÔNG tự `git push`.
- ⚠️ Windows: chạy mọi CLI/pytest có in tiếng Việt với `PYTHONIOENCODING=utf-8` (bẫy cp1252 đã ghi
  ở `docs/inbox-vsc.md`).

## File Structure

```
src/distill/
  __init__.py
  teacher_config.py     # load_teacher_config() -> AgentConfig từ TEACHER_* env (reuse AgentConfig)
  trace_generator.py    # generate_trace(...) -> TraceResult: mirror answer_question + GHI messages
  collect.py            # collect_verified_trace(...): rejection sampling + is_correct → trace|None
  cli.py                # python -m distill.generate (cache/resume), python -m distill.build_dataset
  dataset_builder.py    # traces -> SFT JSONL (format student), loại DevSet, dedupe, metadata
  error_analysis.py     # classify_outcomes(preds, gold) -> Counter (correct/wrong_VALUE/.../abstain)
scripts/
  kaggle_qlora.py       # QLoRA Coder-7B trên Kaggle (torch/unsloth/trl) — KHÔNG test pytest
tests/distill/
  __init__.py
  test_teacher_config.py
  test_trace_generator.py
  test_collect.py
  test_cli.py
  test_dataset_builder.py
  test_error_analysis.py
specs/008-distill-finetune/
  KAGGLE.md             # hướng dẫn chạy kaggle_qlora.py + smoke run + tuân thủ (model card)
```

## Reuse map (chữ ký thật đã đọc)

| Cần | Dùng lại | Chữ ký |
|---|---|---|
| Config teacher | `reasoning_agent.config.AgentConfig` | `AgentConfig(model, base_url, api_key)` |
| Gọi LLM | `reasoning_agent.llm_client.call_chat_completion` | `(config, messages, tools, timeout, temperature=, seed=) -> {content, tool_calls}` |
| Wiring agent | `reasoning_agent.agent.answer_question` | `(question, business_id, as_of_date, dataset_dir, options=None) -> dict` |
| Vòng ReAct | `reasoning_agent.react_loop.run_react_loop` | `(chat_fn, system_prompt, question, tool_registry) -> dict` |
| Verify gold | `eval_harness.matchers.is_correct` | `(truth_type, predicted, truth_answer, alias) -> bool` |
| DevSet | `accuracy_boost.devset.build_devset` | `(questions, answers_by_id, size=200, seed=42, min_per_type=2) -> list` |
| Đo PA | `accuracy_boost.measure` + `eval_harness` | (CLI `collect`/`report` đã có) |

## Quyết định thiết kế (lúc viết plan)

- **Ghi trace KHÔNG sửa lõi 004**: `generate_trace` dựng registry+prompt như `answer_question`
  nhưng truyền một `recording_chat_fn` bọc teacher: nó lưu `messages` của lần gọi cuối cùng, cộng
  thêm assistant-turn chứa `submit_answer` mà chính nó trả về → tái dựng đủ mảng `messages` (vì
  `run_react_loop` không return messages). Không đụng `react_loop.py`/`agent.py`.
- **Verify là nội tại**: SQL chạy thật trong `run_react_loop` lúc teacher chạy; `generate_trace`
  trả cả `result` (đáp án cuối) lẫn `messages`. `collect` gọi `is_correct(result, gold)` — đúng thì
  giữ `messages`, sai thì bỏ. Không có đường nào trace sai lọt vào dataset (FR-002).
- **Rejection sampling**: lần 0 `temperature=0.0` (greedy), lần ≥1 `temperature=0.7, seed=base+i`;
  dừng ở `max_attempts` (env `DISTILL_MAX_ATTEMPTS`, mặc định 3). Dừng ngay khi verify đúng.
- **Cache/resume theo `question_id`**: CLI ghi append từng trace verified (+ dòng "failed" cho câu
  bỏ) vào JSONL; chạy lại bỏ qua id đã có → tất định + tiết kiệm quota cổng free (rate-limit).
- **Teacher phải hỗ trợ function-calling** (tools_payload của 004). Groq Llama-3.3-70B / nhiều model
  OpenRouter có. Nếu model free chọn không hỗ trợ tool → `generate_trace` sẽ không ra trace → đổi model.
- **SFT format = chính mảng `messages`** (system/user/assistant+tool_calls/tool/.../assistant+submit).
  Dataset builder giữ nguyên để student học đúng format inference; train trên assistant-turns
  (loss mask do script Kaggle lo). Dedupe theo hash `messages` chuẩn hoá.
- **Student mặc định Coder-7B**; nếu 7B chạm trần, mở 14B QLoRA (2×T4) — ngoài phạm vi plan này (YAGNI).
- **Đo PA** tái dùng `accuracy_boost.measure` (trỏ `REASONING_AGENT_MODEL` vào base vs fine-tuned);
  `error_analysis.classify_outcomes` cho bảng phân loại lỗi (SC-003, wrong_VALUE giảm). Chạy trên
  Kaggle T4 (fit VRAM) để bỏ nhiễu abstain_budget của RTX 3050.

## Tasks (tóm tắt — chi tiết + test code ở `distill-finetune-tasks.md`)

1. **Teacher config** — `load_teacher_config()` đọc `TEACHER_*` env, reuse `AgentConfig`.
2. **Trace generator** — `generate_trace(...)` mirror `answer_question` + `recording_chat_fn` ghi
   `messages`; trả `TraceResult(result, messages, tool_calls_used)`. Inject được `chat_completion_fn`.
3. **Verified collection** — `collect_verified_trace(...)` rejection sampling + `is_correct` → trace|None.
4. **Generation CLI** — `python -m distill.generate` lặp `train/`, loại DevSet, cache/resume, backoff.
5. **SFT dataset builder** — `python -m distill.build_dataset` → JSONL format student, dedupe, loại DevSet.
6. **QLoRA script (Kaggle)** — `scripts/kaggle_qlora.py` + `KAGGLE.md` (deps chỉ ở Kaggle; smoke run).
7. **Eval + error analysis** — `error_analysis.classify_outcomes` + quy trình đo PA baseline vs tuned.

## Self-Review (đã chạy)

- **Spec coverage**: US1→T2/T3/T4 · US2→T6 · US3→T7 · US4→T6(KAGGLE.md)+đóng gói 006 · FR-001..011
  đều có task; FR-006/FR-009 là ràng buộc + khai báo (KAGGLE.md), không cần code mới.
- **Placeholder scan**: không "TBD/TODO"; mọi task có chữ ký + test thật ở tasks.md.
- **Type consistency**: `generate_trace`→`TraceResult`; `collect_verified_trace`→`VerifiedTrace|None`;
  `is_correct(truth_type, predicted, truth_answer, alias)` khớp chữ ký thật đã đọc; `AgentConfig`
  3 field khớp `config.py`.
