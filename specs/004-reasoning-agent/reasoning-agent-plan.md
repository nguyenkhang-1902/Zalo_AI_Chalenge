# Reasoning Agent (004) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây `answer_question(question, business_id, as_of_date, dataset_dir) -> {"type", "answer"}`
— agent ReAct tool-calling tự suy luận trên dữ liệu đã build sẵn bởi `001-data-loader`, dùng
`002-date-calendar-resolver` để giải nghĩa thời gian tương đối, sinh SQL query DuckDB, và chấm thử
qua `003-eval-harness`.

**Architecture:** 1 module mới `src/reasoning_agent/`. Luồng: `agent.py`'s `answer_question()` mở
DuckDB read-only + đọc `schema.json`/`rulebook.md`/`calendar.csv` của `dataset_dir`, build system
prompt (schema + rulebook) + registry ~15 tool (1 `run_sql`, 12 tool `date_resolver`, `get_readme`,
`get_table_detail`, 1 `submit_answer` nội bộ dùng để kết thúc vòng ReAct), rồi gọi
`react_loop.run_react_loop()` — vòng lặp gọi model LLM qua `llm_client.py` (HTTP OpenAI-compatible,
model-agnostic), dispatch tool call model yêu cầu, lặp tới khi model gọi `submit_answer` hoặc hết
ngân sách (6 tool-call hoặc 45s). KHÔNG code-exec arbitrary — chỉ function-calling có schema cố
định, đúng quyết định đã duyệt.

**Tech Stack:** Python, DuckDB (read-only connection), `urllib` stdlib cho HTTP client (không thêm
dependency `openai`/`httpx` — OpenAI-compatible JSON format đủ đơn giản để tự POST), pytest.

**Spec:** `specs/004-reasoning-agent/spec.md` (đã Khang duyệt, commit `0a9c419`).

## Global Constraints

Copy verbatim từ `.specify/memory/constitution.md` + `specs/004-reasoning-agent/spec.md` — áp
dụng cho MỌI task dưới đây:

- **Điều 1 (Đơn giản & dùng tính năng sẵn có)**: không thêm dependency mới cho HTTP client (dùng
  `urllib` stdlib) — model LLM thật được phục vụ qua 1 server OpenAI-compatible bên ngoài (Ollama/
  vLLM/llama.cpp), không phải thứ project này cài đặt.
- **Điều 9 (Output rõ ràng, reproducible)**: `temperature=0.0`, `seed` cố định trong mọi lời gọi
  model (FR-008) — hằng số module-level trong `llm_client.py`, không phải giá trị cấu hình qua
  env (chỉ model/endpoint mới qua env, theo FR-007).
- **Điều 10 (🔒 Tuân thủ luật cuộc thi)**: không hard-code theo `business_id`/`question_id` cụ thể
  ở bất kỳ đâu trong source (FR-009/SC-004); tổng tham số model ≤15B lúc inference (quyết định ở
  004 là KHÔNG tự chọn model cứng trong code — đọc từ env, người vận hành chịu trách nhiệm chọn
  model ≤15B khi set env, xem C2).
- **Điều 11 (Giữ nguyên ngữ cảnh tiếng Việt)**: system prompt, mô tả tool, message lỗi trả về
  model đều viết tiếng Việt (dữ liệu/câu hỏi/rulebook đều tiếng Việt).
- **FR-001**: `answer_question(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict`
  trả `{"type": str, "answer": Any}`, `type` ∈ 8 kiểu rulebook §9.
- **FR-002**: system prompt MUST đọc `schema.json` (tên bảng/cột/dtype) + `rulebook.md` nguyên văn
  của chính `dataset_dir` lúc runtime — không bake cứng.
- **FR-003**: tool `run_sql` (DuckDB read-only) + 12 tool `date_resolver` 1:1 + `get_readme` +
  `get_table_detail` — danh sách tool đóng, không thêm tool nghiệp vụ nào khác ngoài `submit_answer`
  (cơ chế kết thúc vòng lặp, quyết định ở plan này — xem Task 5).
- **FR-004**: mọi tool trong 12 tool `date_resolver` MUST trả `start`, `end`, `query_end = min(end, as_of_date)`.
  **Đính chính lúc viết plan**: `shift_session` trả `{"session": "sáng"|"chiều"|null}` — hàm gốc
  không có khái niệm khoảng ngày (nhận giờ, trả nhãn ca), nên guard `query_end` không áp dụng cho
  tool này; 11 tool còn lại đều trả đủ `start`/`end`/`query_end`.
- **FR-005**: ReAct tối đa 6 tool-call-step, tổng 45s/câu hỏi; vượt ngưỡng MUST trả
  `{"type": "unanswerable", "reason": "hết ngân sách bước suy luận"}`, không raise/treo.
- **FR-006**: quyết định nội dung `unanswerable` (ngoài guard FR-005) hoàn toàn do model — không
  rule cứng nào trong code quyết định thay.
- **FR-007/FR-008**: model/endpoint qua env var, KHÔNG hard-code ở bất kỳ đâu trong source
  (`grep` phải sạch — SC-003); temperature=0/seed cố định.
- **FR-009**: không rẽ nhánh theo `business_id`/`question_id` cụ thể (SC-004).
- **FR-010**: `answer` không cần đúng tuyệt đối format cuối rulebook §9 — chỉ cần đúng nội dung +
  đúng `type`. Chuẩn hoá format thuộc `005-answer-formatter`.

## Quyết định thiết kế bổ sung (không có trong spec, chốt ở plan này)

1. **Cơ chế kết thúc vòng ReAct**: thêm 1 tool nội bộ `submit_answer(type, answer_json, reason?)`
   — model PHẢI gọi tool này để trả đáp án cuối cùng (không parse free-text). Đây là cơ chế điều
   khiển luồng, không phải "tool nghiệp vụ" nên không vi phạm danh sách đóng ở FR-003.
   `answer_json` là chuỗi JSON-encode giá trị đáp án (vd `"4820000"`, `"[1,2,3]"`,
   `"{\"columns\":[...],\"rows\":[...]}"`) — tránh vấn đề JSON-schema không mô tả được tham số đa
   kiểu của chuẩn OpenAI function-calling.
2. **Đếm ngân sách 6 tool-call**: tính MỌI lượt gọi tool (kể cả `submit_answer` tính vào 6) — đọc
   literal "6 lượt gọi tool" của FR-005. Kiểm tra ngân sách TRƯỚC mỗi tool-call riêng lẻ (không
   phải trước mỗi lượt LLM) — nếu 1 lượt LLM trả nhiều tool_call cùng lúc mà tool_call thứ k vượt
   ngân sách, dừng NGAY tại đó, không dispatch tool_call thứ k, trả unanswerable.
3. **Guard lỗi tool đồng nhất**: 1 wrapper dispatch DUY NHẤT trong `react_loop.py` bắt MỌI exception
   từ handler (tool không tồn tại, JSON tham số hỏng, thiếu tham số bắt buộc, lỗi logic riêng của
   tool) → trả `{"error": str(e)}` cho model, không raise ra ngoài loop. `run_sql` còn tự bắt lỗi
   DuckDB bên trong chính nó (yêu cầu rõ của FR-003), wrapper là lớp bảo vệ thứ 2 cho MỌI tool khác.
4. **Giới hạn thời gian thật**: mỗi lời gọi HTTP tới model server dùng `timeout=<ngân sách còn
   lại>` của `urllib.request.urlopen` — chặn cứng bằng socket timeout thật, không chỉ đo bằng
   đồng hồ sau khi gọi xong.
5. **`answer_question` đóng kết nối DuckDB** bằng `try/finally` sau khi vòng ReAct kết thúc (thành
   công hoặc hết ngân sách) — tránh leak file handle khi gọi lặp lại nhiều lần (Task 7: 100 câu).

## Project Structure

### Source Code (mới)
```
src/reasoning_agent/
├── __init__.py        # re-export answer_question
├── config.py           # AgentConfig, load_config() — FR-007
├── llm_client.py        # call_chat_completion() — HTTP OpenAI-compatible, FR-007/FR-008
├── date_tools.py         # build_date_tool_registry() — FR-003 (12 tool) + FR-004 (query_end)
├── sql_tool.py           # build_sql_tool() — FR-003 (run_sql, DuckDB read-only)
├── schema_tools.py       # load_schema(), build_schema_tools() — FR-003 (get_readme/get_table_detail)
├── prompt.py             # build_system_prompt() — FR-002
├── react_loop.py         # ToolSpec, run_react_loop(), submit_answer — FR-005/FR-006, Quyết định 1-4
└── agent.py              # answer_question() — FR-001, wiring toàn bộ, Quyết định 5
```

### Test Code (mới)
```
tests/reasoning_agent/
├── __init__.py
├── conftest.py                  # build_real_business() helper — build thật 1 business vào tmp_path
├── test_config.py
├── test_llm_client.py
├── test_date_tools.py
├── test_schema_tools_and_prompt.py
├── test_sql_tool.py
├── test_react_loop.py
├── test_agent.py
└── test_baseline_golden.py      # Task 7 — SC-001/SC-002, cần model server thật đang chạy
```

## ⚠️ Complexity Tracking

Không có vi phạm Constitution Check cần biện minh — kiến trúc tool-calling + ReAct đã được Khang
duyệt trực tiếp trong brainstorming, không có lựa chọn đơn giản hơn bị loại.
