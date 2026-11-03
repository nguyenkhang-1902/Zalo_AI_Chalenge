# Answer Formatter (005) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Task text lives in `specs/005-answer-formatter/answer-formatter-tasks.md` — read that file for the actual `### Task N` sections.

**Goal:** Xây `run_batch(questions_path, dataset_dir, out_path, concurrency, limit, answer_fn) ->
BatchSummary` — chạy `answer_question` (004) cho cả 1 bộ `questions.jsonl`, chuẩn hoá đáp án theo
`rulebook.md` §9, ghi `submission.jsonl` mà `score_submission` (003) đọc được, có resume +
concurrency cho quy mô ngàn câu.

**Architecture:** 1 module mới `src/answer_formatter/`. `normalize.py` chuẩn hoá đáp án thuần
(không I/O). `runner.py` là lõi: đọc `questions.jsonl`, guard dữ liệu lỗi (id trùng, concurrency
sai), tính resume-set từ file output cũ (khoan dung), dispatch qua `ThreadPoolExecutor`, ghi mỗi
dòng ngay (flush + lock) — không đợi hết batch. `cli.py` là wrapper argparse mỏng gọi `run_batch`
với `answer_question` thật.

**Tech Stack:** Python stdlib (`concurrent.futures.ThreadPoolExecutor`, `threading.Lock`, `json`,
`argparse`) — không thêm dependency mới. pytest cho test.

**Spec:** `specs/005-answer-formatter/spec.md` (đã Khang duyệt, commit `8773ef3`, sửa chữ ký
`answer_fn` ở commit `fffcbd2`).

## Global Constraints

Copy verbatim từ `.specify/memory/constitution.md` + `specs/005-answer-formatter/spec.md` — áp
dụng cho MỌI task dưới đây:

- **Điều 1 (Đơn giản & dùng tính năng sẵn có)**: không thêm dependency mới — `ThreadPoolExecutor`
  stdlib đủ cho concurrency (FR-004), không cần `asyncio`/thư viện queue ngoài.
- **Điều 7 (Suy giảm duyên dáng)**: 1 câu hỏi lỗi không được làm sập cả batch ngàn câu (FR-007).
- **Điều 10 (🔒 Tuân thủ luật cuộc thi)**: không rẽ nhánh theo `business_id`/`question_id` cụ thể
  ở bất kỳ đâu trong source (áp dụng xuyên suốt dự án, 005 không có FR riêng nhưng vẫn phải giữ).
- **FR-001**: `run_batch(questions_path: Path, dataset_dir: Path, out_path: Path,
  concurrency: int = 1, limit: int | None = None, answer_fn: Callable[[str, str, date, Path],
  dict] = answer_question) -> BatchSummary`. `answer_fn` nhận ĐỦ 4 tham số khớp chữ ký thật của
  `answer_question` (004) — `run_batch` tự truyền `dataset_dir` của chính nó vào mỗi lời gọi.
- **FR-002**: đọc `questions_path` JSONL `{"id", "business_id", "question", "as_of_date"}`,
  `as_of_date` parse bằng `date.fromisoformat`.
- **FR-003**: nếu `out_path` đã tồn tại, đọc trước khoan dung (bỏ dòng rỗng/JSON hỏng/thiếu
  `"id"`, không raise) để tính resume-set.
- **FR-004**: `ThreadPoolExecutor(max_workers=concurrency)`; `concurrency=1` phải cho kết quả
  tương đương tuần tự.
- **FR-005**: mỗi câu xử lý xong (thành công hoặc lỗi) MUST ghi ngay 1 dòng (append + flush),
  dùng lock chống ghi chồng giữa worker.
- **FR-006**: dòng ghi `{"id": ..., "type": ..., "answer": ...}` hoặc `{"id": ..., "type":
  "unanswerable", "reason": ...}` — khớp `_load_submission` của 003.
- **FR-007**: `answer_fn` raise exception HOẶC trả giá trị sai hợp đồng (không phải dict/thiếu
  `"type"`/thiếu `"answer"` khi `type != "unanswerable"`) → ghi `{"type": "unanswerable",
  "reason": "lỗi xử lý: <mô tả>"}`, KHÔNG dừng batch.
- **FR-008**: chuẩn hoá — `percent` (số, không phải `bool`) → `round(answer, 2)`; `table` (dict)
  → map alias cố định `"cols"`→`"columns"`, `"data"`/`"records"`→`"rows"`, key lạ giữ nguyên. Các
  type khác pass-through nguyên văn.
- **FR-009**: `limit` chỉ áp dụng lên phần CHƯA resume-skip.
- **FR-010**: CLI `--questions`, `--dataset-dir`, `--out`, `--concurrency` (default 1), `--limit`
  (optional).
- **FR-011**: raise lỗi rõ ngay từ đầu (trước khi xử lý bất kỳ câu nào) nếu `id` trùng trong
  `questions_path`, hoặc `concurrency < 1`.
- **FR-012**: trả `BatchSummary` gồm `total`, `resumed_skipped`, `processed`, `errored`,
  `elapsed_seconds`.

## Project Structure

### Source Code (mới)
```
src/answer_formatter/
├── __init__.py     # re-export run_batch, BatchSummary — FR-001/FR-012
├── normalize.py    # normalize_answer() — FR-008
├── runner.py       # BatchSummary, run_batch() — FR-001..FR-007, FR-009, FR-011, FR-012
└── cli.py          # main() argparse — FR-010
```

### Test Code (mới)
```
tests/answer_formatter/
├── __init__.py
├── conftest.py                      # TRAIN_DIR + build_real_dataset() — build thật qua 001
├── test_normalize.py                # Task 1 — FR-008
├── test_runner_basic.py             # Task 2 — FR-001/002/003/005/006/007/009/011/012
├── test_runner_concurrency.py       # Task 3 — FR-004/SC-003
├── test_cli.py                      # Task 4 — FR-010
├── test_full_scale_fake.py              # Task 5 — SC-001, 3000 câu train/ thật, answer_fn giả
├── test_sc002_resume_after_interruption.py  # Task 5 — SC-002, resume sau khi bị dừng giữa chừng
└── test_sc004_real_integration.py       # Task 5 — SC-004, cần model server thật đang chạy
```

## ⚠️ Complexity Tracking

Không có vi phạm Constitution Check cần biện minh — kiến trúc batch runner + CLI mỏng đã được
Khang duyệt trực tiếp trong brainstorming, không có lựa chọn đơn giản hơn bị loại.
