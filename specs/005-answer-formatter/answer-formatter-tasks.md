# Answer Formatter (005) — Tasks

> Đọc kèm `specs/005-answer-formatter/answer-formatter-plan.md` (Goal/Architecture/Global
> Constraints) và `specs/005-answer-formatter/spec.md` (nguồn yêu cầu đầy đủ) trước khi thực thi
> bất kỳ task nào.

### Task 1: `normalize_answer` — chuẩn hoá percent + table (FR-008)

**Files:**
- Create: `src/answer_formatter/normalize.py`
- Test: `tests/answer_formatter/test_normalize.py`

**Interfaces:**
- Produces: `normalize_answer(result: dict) -> dict` — dùng bởi Task 2's `run_batch`.

- [ ] **Step 1: Write the failing test**

```python
"""Test normalize_answer — FR-008, xem specs/005-answer-formatter/spec.md."""
from __future__ import annotations

from answer_formatter.normalize import normalize_answer


def test_rounds_percent_to_two_decimals():
    result = {"type": "percent", "answer": 12.398572}
    assert normalize_answer(result) == {"type": "percent", "answer": 12.4}


def test_percent_boolean_answer_not_touched():
    result = {"type": "percent", "answer": True}
    assert normalize_answer(result) == {"type": "percent", "answer": True}


def test_percent_non_numeric_answer_not_touched():
    result = {"type": "percent", "answer": "12.4%"}
    assert normalize_answer(result) == {"type": "percent", "answer": "12.4%"}


def test_table_alias_keys_mapped_to_canonical():
    result = {"type": "table", "answer": {"cols": ["a", "b"], "data": [[1, 2]]}}
    assert normalize_answer(result) == {
        "type": "table",
        "answer": {"columns": ["a", "b"], "rows": [[1, 2]]},
    }


def test_table_records_alias_mapped_to_rows():
    result = {"type": "table", "answer": {"columns": ["a"], "records": [[1]]}}
    assert normalize_answer(result) == {
        "type": "table",
        "answer": {"columns": ["a"], "rows": [[1]]},
    }


def test_table_unknown_keys_kept_unchanged():
    result = {"type": "table", "answer": {"headers": ["a"], "body": [[1]]}}
    assert normalize_answer(result) == result


def test_number_type_passes_through_unchanged():
    result = {"type": "number", "answer": 5}
    assert normalize_answer(result) == result


def test_unanswerable_passes_through_unchanged():
    result = {"type": "unanswerable", "reason": "không đủ dữ liệu"}
    assert normalize_answer(result) == result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/answer_formatter/test_normalize.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'answer_formatter'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Chuẩn hoá format đáp án trước khi ghi submission — FR-008, xem
specs/005-answer-formatter/spec.md."""
from __future__ import annotations

_TABLE_KEY_ALIASES: dict[str, str] = {
    "columns": "columns",
    "cols": "columns",
    "rows": "rows",
    "data": "rows",
    "records": "rows",
}


def normalize_answer(result: dict) -> dict:
    result_type = result.get("type")
    answer = result.get("answer")

    if result_type == "percent" and isinstance(answer, (int, float)) and not isinstance(answer, bool):
        return {**result, "answer": round(answer, 2)}

    if result_type == "table" and isinstance(answer, dict):
        normalized_answer = {_TABLE_KEY_ALIASES.get(key, key): value for key, value in answer.items()}
        return {**result, "answer": normalized_answer}

    return result
```

Cần `src/answer_formatter/__init__.py` rỗng (hoặc `from __future__ import annotations` thôi) để
`pythonpath = src` (xem `pytest.ini`) nhận diện package — tạo file rỗng tạm, Task 4 sẽ điền
`__all__` thật:

```python
```

(file `src/answer_formatter/__init__.py` để trống hoàn toàn ở bước này.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/answer_formatter/test_normalize.py -v`
Expected: PASS (8 test)

- [ ] **Step 5: Commit**

```bash
git add src/answer_formatter/__init__.py src/answer_formatter/normalize.py tests/answer_formatter/__init__.py tests/answer_formatter/test_normalize.py
git commit -m "feat: add answer_formatter.normalize_answer (FR-008)"
```

(Tạo `tests/answer_formatter/__init__.py` rỗng cùng lúc nếu chưa có.)

---

### Task 2: `run_batch` tuần tự — resume, limit, lỗi, guard (FR-001/002/003/005/006/007/009/011/012)

**Files:**
- Create: `src/answer_formatter/runner.py`
- Test: `tests/answer_formatter/test_runner_basic.py`

**Interfaces:**
- Consumes: `normalize_answer(result: dict) -> dict` (Task 1).
- Produces: `BatchSummary` (dataclass: `total: int, resumed_skipped: int, processed: int,
  errored: int, elapsed_seconds: float`), `run_batch(questions_path: Path, dataset_dir: Path,
  out_path: Path, concurrency: int = 1, limit: int | None = None, answer_fn:
  Callable[[str, str, date, Path], dict] = answer_question) -> BatchSummary` — Task 3 sẽ THAY
  TOÀN BỘ nội dung hàm `run_batch` (vẫn giữ nguyên chữ ký) để thêm concurrency thật; mọi test ở
  task này phải tiếp tục PASS sau khi Task 3 xong.

- [ ] **Step 1: Write the failing test**

```python
"""Test run_batch (tuần tự) — FR-001/002/003/005/006/007/009/011/012, xem
specs/005-answer-formatter/spec.md."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from answer_formatter.runner import run_batch


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _fake_answer_fn(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
    return {"type": "string", "answer": f"{business_id}:{question}"}


def test_basic_run_writes_one_line_per_question(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "q1", "business_id": "biz_1", "question": "hỏi 1", "as_of_date": "2026-01-01"},
        {"id": "q2", "business_id": "biz_2", "question": "hỏi 2", "as_of_date": "2026-01-02"},
    ])
    out_path = tmp_path / "submission.jsonl"

    summary = run_batch(questions_path, tmp_path, out_path, answer_fn=_fake_answer_fn)

    rows = _read_jsonl(out_path)
    assert {r["id"] for r in rows} == {"q1", "q2"}
    assert next(r for r in rows if r["id"] == "q1")["answer"] == "biz_1:hỏi 1"
    assert summary.total == 2
    assert summary.resumed_skipped == 0
    assert summary.processed == 2
    assert summary.errored == 0
    assert summary.elapsed_seconds >= 0


def test_resume_skips_already_done_ids(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "q1", "business_id": "biz_1", "question": "hỏi 1", "as_of_date": "2026-01-01"},
        {"id": "q2", "business_id": "biz_2", "question": "hỏi 2", "as_of_date": "2026-01-02"},
    ])
    out_path = tmp_path / "submission.jsonl"
    _write_jsonl(out_path, [{"id": "q1", "type": "string", "answer": "cũ"}])

    calls: list[str] = []

    def tracking_fn(question, business_id, as_of_date, dataset_dir):
        calls.append(business_id)
        return {"type": "string", "answer": "mới"}

    summary = run_batch(questions_path, tmp_path, out_path, answer_fn=tracking_fn)

    assert calls == ["biz_2"]
    rows = _read_jsonl(out_path)
    assert len(rows) == 2
    assert next(r for r in rows if r["id"] == "q1")["answer"] == "cũ"
    assert summary.resumed_skipped == 1
    assert summary.processed == 1


def test_resume_tolerates_malformed_lines_in_old_output(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "q1", "business_id": "biz_1", "question": "hỏi 1", "as_of_date": "2026-01-01"},
    ])
    out_path = tmp_path / "submission.jsonl"
    out_path.write_text('khong phai json\n\n{"type": "string"}\n', encoding="utf-8")

    summary = run_batch(questions_path, tmp_path, out_path, answer_fn=_fake_answer_fn)

    assert summary.resumed_skipped == 0
    assert summary.processed == 1


def test_limit_applies_only_to_remaining_after_resume(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": f"q{i}", "business_id": "biz_1", "question": "hỏi", "as_of_date": "2026-01-01"}
        for i in range(5)
    ])
    out_path = tmp_path / "submission.jsonl"
    _write_jsonl(out_path, [{"id": "q0", "type": "string", "answer": "cũ"}])

    summary = run_batch(questions_path, tmp_path, out_path, limit=2, answer_fn=_fake_answer_fn)

    assert summary.resumed_skipped == 1
    assert summary.processed == 2
    rows = _read_jsonl(out_path)
    assert len(rows) == 3


def test_duplicate_id_in_questions_raises_before_processing(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "dup", "business_id": "biz_1", "question": "a", "as_of_date": "2026-01-01"},
        {"id": "dup", "business_id": "biz_2", "question": "b", "as_of_date": "2026-01-01"},
    ])
    out_path = tmp_path / "submission.jsonl"
    calls: list[str] = []

    def tracking_fn(question, business_id, as_of_date, dataset_dir):
        calls.append(business_id)
        return {"type": "string", "answer": "x"}

    with pytest.raises(ValueError, match="trùng lặp"):
        run_batch(questions_path, tmp_path, out_path, answer_fn=tracking_fn)
    assert calls == []
    assert not out_path.exists()


def test_concurrency_below_one_raises(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [])
    out_path = tmp_path / "submission.jsonl"

    with pytest.raises(ValueError, match="concurrency"):
        run_batch(questions_path, tmp_path, out_path, concurrency=0, answer_fn=_fake_answer_fn)


def test_exception_in_answer_fn_written_as_unanswerable_and_batch_continues(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "q1", "business_id": "biz_1", "question": "lỗi", "as_of_date": "2026-01-01"},
        {"id": "q2", "business_id": "biz_2", "question": "ổn", "as_of_date": "2026-01-01"},
    ])
    out_path = tmp_path / "submission.jsonl"

    def flaky_fn(question, business_id, as_of_date, dataset_dir):
        if business_id == "biz_1":
            raise RuntimeError("giả lập lỗi mạng")
        return {"type": "string", "answer": "ổn"}

    summary = run_batch(questions_path, tmp_path, out_path, answer_fn=flaky_fn)

    rows = {r["id"]: r for r in _read_jsonl(out_path)}
    assert rows["q1"]["type"] == "unanswerable"
    assert "giả lập lỗi mạng" in rows["q1"]["reason"]
    assert rows["q2"]["type"] == "string"
    assert summary.errored == 1
    assert summary.processed == 2


def test_contract_violation_treated_as_error(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "q1", "business_id": "biz_1", "question": "a", "as_of_date": "2026-01-01"},
    ])
    out_path = tmp_path / "submission.jsonl"

    def broken_fn(question, business_id, as_of_date, dataset_dir):
        return {"type": "number"}  # thiếu "answer"

    summary = run_batch(questions_path, tmp_path, out_path, answer_fn=broken_fn)

    rows = _read_jsonl(out_path)
    assert rows[0]["type"] == "unanswerable"
    assert summary.errored == 1


def test_percent_answer_normalized_before_write(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "q1", "business_id": "biz_1", "question": "a", "as_of_date": "2026-01-01"},
    ])
    out_path = tmp_path / "submission.jsonl"

    def percent_fn(question, business_id, as_of_date, dataset_dir):
        return {"type": "percent", "answer": 12.398572}

    run_batch(questions_path, tmp_path, out_path, answer_fn=percent_fn)

    rows = _read_jsonl(out_path)
    assert rows[0]["answer"] == 12.4


def test_limit_zero_processes_nothing(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "q1", "business_id": "biz_1", "question": "a", "as_of_date": "2026-01-01"},
    ])
    out_path = tmp_path / "submission.jsonl"
    calls: list[str] = []

    def tracking_fn(question, business_id, as_of_date, dataset_dir):
        calls.append(business_id)
        return {"type": "string", "answer": "x"}

    summary = run_batch(questions_path, tmp_path, out_path, limit=0, answer_fn=tracking_fn)

    assert calls == []
    assert summary.processed == 0
    assert summary.total == 1


def test_creates_missing_parent_directory_for_out_path(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "q1", "business_id": "biz_1", "question": "a", "as_of_date": "2026-01-01"},
    ])
    out_path = tmp_path / "nested" / "dir" / "submission.jsonl"

    run_batch(questions_path, tmp_path, out_path, answer_fn=_fake_answer_fn)

    assert out_path.exists()
    assert len(_read_jsonl(out_path)) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/answer_formatter/test_runner_basic.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'answer_formatter.runner'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Batch runner (tuần tự) — FR-001/002/003/005/006/007/009/011/012, xem
specs/005-answer-formatter/spec.md. Task 3 sẽ thay nội dung run_batch để thêm concurrency thật,
giữ nguyên chữ ký."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from answer_formatter.normalize import normalize_answer
from reasoning_agent import answer_question

AnswerFn = Callable[[str, str, date, Path], dict]


@dataclass
class BatchSummary:
    total: int
    resumed_skipped: int
    processed: int
    errored: int
    elapsed_seconds: float


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_done_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    done: set[str] = set()
    with out_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                done.add(row["id"])
    return done


def _validate_contract(result: object) -> None:
    if not isinstance(result, dict):
        raise ValueError(f"answer_fn phải trả dict, nhận {type(result).__name__}")
    if "type" not in result:
        raise ValueError("answer_fn thiếu key 'type'")
    if result["type"] != "unanswerable" and "answer" not in result:
        raise ValueError("answer_fn thiếu key 'answer' (type khác unanswerable)")


def _answer_one(question: dict, dataset_dir: Path, answer_fn: AnswerFn) -> tuple[dict, bool]:
    as_of = date.fromisoformat(question["as_of_date"])
    try:
        result = answer_fn(question["question"], question["business_id"], as_of, dataset_dir)
        _validate_contract(result)
    except Exception as exc:  # noqa: BLE001 - 1 câu lỗi không được sập cả batch (FR-007)
        return {"type": "unanswerable", "reason": f"lỗi xử lý: {exc}"}, True
    return normalize_answer(result), False


def run_batch(
    questions_path: Path,
    dataset_dir: Path,
    out_path: Path,
    concurrency: int = 1,
    limit: int | None = None,
    answer_fn: AnswerFn = answer_question,
) -> BatchSummary:
    if concurrency < 1:
        raise ValueError(f"concurrency phải >= 1, nhận {concurrency}")

    start = time.monotonic()
    questions = _load_jsonl(questions_path)

    seen_ids: set[str] = set()
    for q in questions:
        if q["id"] in seen_ids:
            raise ValueError(f"id trùng lặp trong questions_path: {q['id']}")
        seen_ids.add(q["id"])

    done_ids = _load_done_ids(out_path)
    remaining = [q for q in questions if q["id"] not in done_ids]
    if limit is not None:
        remaining = remaining[:limit]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    errored = 0
    with out_path.open("a", encoding="utf-8") as out_file:
        for q in remaining:
            result, is_error = _answer_one(q, dataset_dir, answer_fn)
            if is_error:
                errored += 1
            out_file.write(json.dumps({"id": q["id"], **result}, ensure_ascii=False) + "\n")
            out_file.flush()

    return BatchSummary(
        total=len(questions),
        resumed_skipped=len(done_ids & seen_ids),
        processed=len(remaining),
        errored=errored,
        elapsed_seconds=time.monotonic() - start,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/answer_formatter/test_runner_basic.py -v`
Expected: PASS (11 test)

- [ ] **Step 5: Commit**

```bash
git add src/answer_formatter/runner.py tests/answer_formatter/test_runner_basic.py
git commit -m "feat: add answer_formatter.run_batch sequential core (FR-001..FR-012 minus concurrency)"
```

---

### Task 3: Concurrency thật qua `ThreadPoolExecutor` (FR-004, SC-003)

**Files:**
- Modify: `src/answer_formatter/runner.py` (thay toàn bộ nội dung hàm `run_batch`, giữ nguyên
  chữ ký; các hàm `_load_jsonl`/`_load_done_ids`/`_validate_contract`/`_answer_one` GIỮ NGUYÊN
  không đổi)
- Test: `tests/answer_formatter/test_runner_concurrency.py`

**Interfaces:**
- Consumes: `_answer_one(question, dataset_dir, answer_fn) -> tuple[dict, bool]` (Task 2, không
  đổi).
- Produces: `run_batch(...)` (chữ ký không đổi) — nay thực sự chạy song song khi `concurrency > 1`.

- [ ] **Step 1: Write the failing test**

```python
"""Test concurrency thật — FR-004/SC-003, xem specs/005-answer-formatter/spec.md."""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from answer_formatter.runner import run_batch

_SLEEP_SECONDS = 0.05
_N_QUESTIONS = 20


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _slow_fn(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
    time.sleep(_SLEEP_SECONDS)
    return {"type": "string", "answer": business_id}


def _build_questions(path: Path) -> None:
    _write_jsonl(path, [
        {"id": f"q{i}", "business_id": f"biz_{i}", "question": "a", "as_of_date": "2026-01-01"}
        for i in range(_N_QUESTIONS)
    ])


def test_concurrency_is_meaningfully_faster_than_sequential(tmp_path: Path):
    seq_dir = tmp_path / "seq"
    seq_dir.mkdir()
    questions_path = seq_dir / "questions.jsonl"
    _build_questions(questions_path)
    start = time.monotonic()
    run_batch(questions_path, seq_dir, seq_dir / "out.jsonl", concurrency=1, answer_fn=_slow_fn)
    sequential_elapsed = time.monotonic() - start

    par_dir = tmp_path / "par"
    par_dir.mkdir()
    questions_path2 = par_dir / "questions.jsonl"
    _build_questions(questions_path2)
    start = time.monotonic()
    run_batch(questions_path2, par_dir, par_dir / "out.jsonl", concurrency=4, answer_fn=_slow_fn)
    concurrent_elapsed = time.monotonic() - start

    assert concurrent_elapsed < sequential_elapsed * 0.6, (
        f"concurrency=4 ({concurrent_elapsed:.2f}s) không nhanh hơn rõ rệt so với "
        f"concurrency=1 ({sequential_elapsed:.2f}s)"
    )


def test_concurrency_writes_all_lines_without_duplication_or_loss(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _build_questions(questions_path)
    out_path = tmp_path / "out.jsonl"

    run_batch(questions_path, tmp_path, out_path, concurrency=8, answer_fn=_slow_fn)

    with out_path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    ids = [r["id"] for r in rows]
    assert len(ids) == _N_QUESTIONS
    assert len(set(ids)) == _N_QUESTIONS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/answer_formatter/test_runner_concurrency.py -v`
Expected: FAIL ở `test_concurrency_is_meaningfully_faster_than_sequential` (hiện tại tuần tự thật,
2 lượt chạy mất thời gian gần bằng nhau, assertion `<` sai).

- [ ] **Step 3: Write minimal implementation**

Thay TOÀN BỘ nội dung hàm `run_batch` trong `src/answer_formatter/runner.py` bằng (thêm import
`threading` và `ThreadPoolExecutor` ở đầu file, giữ nguyên mọi hàm khác):

```python
import threading
from concurrent.futures import ThreadPoolExecutor
```

```python
def run_batch(
    questions_path: Path,
    dataset_dir: Path,
    out_path: Path,
    concurrency: int = 1,
    limit: int | None = None,
    answer_fn: AnswerFn = answer_question,
) -> BatchSummary:
    if concurrency < 1:
        raise ValueError(f"concurrency phải >= 1, nhận {concurrency}")

    start = time.monotonic()
    questions = _load_jsonl(questions_path)

    seen_ids: set[str] = set()
    for q in questions:
        if q["id"] in seen_ids:
            raise ValueError(f"id trùng lặp trong questions_path: {q['id']}")
        seen_ids.add(q["id"])

    done_ids = _load_done_ids(out_path)
    remaining = [q for q in questions if q["id"] not in done_ids]
    if limit is not None:
        remaining = remaining[:limit]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    errored = 0
    write_lock = threading.Lock()

    with out_path.open("a", encoding="utf-8") as out_file:
        def _process_and_write(q: dict) -> bool:
            result, is_error = _answer_one(q, dataset_dir, answer_fn)
            line = json.dumps({"id": q["id"], **result}, ensure_ascii=False) + "\n"
            with write_lock:
                out_file.write(line)
                out_file.flush()
            return is_error

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            for is_error in pool.map(_process_and_write, remaining):
                if is_error:
                    errored += 1

    return BatchSummary(
        total=len(questions),
        resumed_skipped=len(done_ids & seen_ids),
        processed=len(remaining),
        errored=errored,
        elapsed_seconds=time.monotonic() - start,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/answer_formatter/test_runner_concurrency.py tests/answer_formatter/test_runner_basic.py -v`
Expected: PASS toàn bộ (cả 2 file — Task 2's test KHÔNG được hỏng).

- [ ] **Step 5: Commit**

```bash
git add src/answer_formatter/runner.py tests/answer_formatter/test_runner_concurrency.py
git commit -m "feat: run answer_formatter batch concurrently via ThreadPoolExecutor (FR-004, SC-003)"
```

---

### Task 4: CLI + package exports (FR-010)

**Files:**
- Create: `src/answer_formatter/cli.py`
- Modify: `src/answer_formatter/__init__.py` (hiện đang rỗng từ Task 1)
- Test: `tests/answer_formatter/test_cli.py`

**Interfaces:**
- Consumes: `run_batch`, `BatchSummary` (Task 2/3, không đổi).
- Produces: `main()` (entry point CLI); package `answer_formatter` export `run_batch`,
  `BatchSummary` ở top-level.

- [ ] **Step 1: Write the failing test**

```python
"""Test CLI — FR-010, xem specs/005-answer-formatter/spec.md."""
from __future__ import annotations

from pathlib import Path

from answer_formatter import cli
from answer_formatter.runner import BatchSummary


def test_cli_parses_args_and_calls_run_batch(tmp_path, monkeypatch, capsys):
    captured = {}

    def fake_run_batch(questions_path, dataset_dir, out_path, concurrency=1, limit=None, **kwargs):
        captured["questions_path"] = questions_path
        captured["dataset_dir"] = dataset_dir
        captured["out_path"] = out_path
        captured["concurrency"] = concurrency
        captured["limit"] = limit
        return BatchSummary(total=1, resumed_skipped=0, processed=1, errored=0, elapsed_seconds=0.1)

    monkeypatch.setattr(cli, "run_batch", fake_run_batch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "answer-formatter",
            "--questions", str(tmp_path / "q.jsonl"),
            "--dataset-dir", str(tmp_path),
            "--out", str(tmp_path / "out.jsonl"),
            "--concurrency", "4",
            "--limit", "10",
        ],
    )

    cli.main()

    assert captured["questions_path"] == Path(tmp_path / "q.jsonl")
    assert captured["dataset_dir"] == Path(tmp_path)
    assert captured["out_path"] == Path(tmp_path / "out.jsonl")
    assert captured["concurrency"] == 4
    assert captured["limit"] == 10

    out = capsys.readouterr().out
    assert "Tổng: 1" in out


def test_cli_limit_defaults_to_none_when_omitted(tmp_path, monkeypatch):
    captured = {}

    def fake_run_batch(questions_path, dataset_dir, out_path, concurrency=1, limit=None, **kwargs):
        captured["limit"] = limit
        captured["concurrency"] = concurrency
        return BatchSummary(total=0, resumed_skipped=0, processed=0, errored=0, elapsed_seconds=0.0)

    monkeypatch.setattr(cli, "run_batch", fake_run_batch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "answer-formatter",
            "--questions", str(tmp_path / "q.jsonl"),
            "--dataset-dir", str(tmp_path),
            "--out", str(tmp_path / "out.jsonl"),
        ],
    )

    cli.main()

    assert captured["limit"] is None
    assert captured["concurrency"] == 1


def test_all_public_symbols_importable_from_package_root():
    from answer_formatter import BatchSummary, run_batch

    assert run_batch is not None
    assert BatchSummary is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/answer_formatter/test_cli.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'answer_formatter.cli'`

- [ ] **Step 3: Write minimal implementation**

`src/answer_formatter/cli.py`:

```python
"""CLI mỏng chạy batch — FR-010, xem specs/005-answer-formatter/spec.md."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from answer_formatter.runner import run_batch


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Chạy answer_question theo lô, ghi submission.jsonl"
    )
    parser.add_argument("--questions", required=True)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    summary = run_batch(
        questions_path=Path(args.questions),
        dataset_dir=Path(args.dataset_dir),
        out_path=Path(args.out),
        concurrency=args.concurrency,
        limit=args.limit,
    )
    print(
        f"Tổng: {summary.total} | resume-skip: {summary.resumed_skipped} | "
        f"xử lý: {summary.processed} | lỗi: {summary.errored} | "
        f"thời gian: {summary.elapsed_seconds:.1f}s"
    )


if __name__ == "__main__":
    main()
```

`src/answer_formatter/__init__.py` (thay nội dung rỗng từ Task 1):

```python
"""Answer formatter — 005-answer-formatter. Public API: run_batch, BatchSummary (FR-001/FR-012)."""
from __future__ import annotations

from answer_formatter.runner import BatchSummary, run_batch

__all__ = ["run_batch", "BatchSummary"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/answer_formatter/test_cli.py -v`
Expected: PASS (3 test)

- [ ] **Step 5: Commit**

```bash
git add src/answer_formatter/cli.py src/answer_formatter/__init__.py tests/answer_formatter/test_cli.py
git commit -m "feat: add answer_formatter CLI + package exports (FR-010)"
```

---

### Task 5: Xác nhận SC-001 (3000 câu thật) + SC-002 (resume sau khi bị dừng) + SC-004 (LLM thật)

**Files:**
- Create: `tests/answer_formatter/conftest.py`
- Create: `tests/answer_formatter/test_full_scale_fake.py`
- Create: `tests/answer_formatter/test_sc002_resume_after_interruption.py`
- Create: `tests/answer_formatter/test_sc004_real_integration.py`

**Interfaces:**
- Consumes: `run_batch` (Task 3), `score_submission` (003, `eval_harness.scoring`),
  `build_business` (001, `data_loader.build_business_db`) — không tạo API mới, đây là task xác
  nhận bằng dữ liệu thật, không có code sản phẩm mới.

- [ ] **Step 1: Write the failing test**

`tests/answer_formatter/conftest.py` (helper build dữ liệu thật, theo đúng pattern
`tests/reasoning_agent/conftest.py` đã dùng ở 004):

```python
"""Helper build dữ liệu thật cho test answer_formatter — build qua chính
data_loader.build_business_db.build_business trên train/ thật, không dùng fixture bịa."""
from __future__ import annotations

import shutil
from pathlib import Path

from data_loader.build_business_db import build_business

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DIR = PROJECT_ROOT / "train"


def build_real_dataset(dataset_dir: Path, business_ids: set[str]) -> None:
    for name in ("rulebook.md", "calendar.csv"):
        shutil.copy(TRAIN_DIR / name, dataset_dir / name)
    for business_id in business_ids:
        build_business(TRAIN_DIR / "data" / business_id, dataset_dir)
```

`tests/answer_formatter/test_full_scale_fake.py` (SC-001 — không `skipif`, chạy luôn vì
`answer_fn` giả không gọi LLM thật, phải nhanh):

```python
"""SC-001: toàn bộ 3000 câu train/questions.jsonl, answer_fn giả tốc độ cao (không gọi LLM thật)
— xác nhận không trùng/thiếu id và submission đọc được bởi 003, xem
specs/005-answer-formatter/spec.md."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from answer_formatter.runner import run_batch
from eval_harness.scoring import score_submission

from .conftest import TRAIN_DIR


def _fast_fake_answer_fn(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
    return {"type": "unanswerable", "reason": "fake test, không gọi LLM thật"}


def test_full_scale_train_questions_produce_valid_submission(tmp_path: Path):
    out_path = tmp_path / "submission.jsonl"

    summary = run_batch(
        questions_path=TRAIN_DIR / "questions.jsonl",
        dataset_dir=TRAIN_DIR,
        out_path=out_path,
        concurrency=8,
        answer_fn=_fast_fake_answer_fn,
    )

    assert summary.total == 3000
    assert summary.processed == 3000
    assert summary.errored == 0

    with out_path.open(encoding="utf-8") as f:
        ids = [json.loads(line)["id"] for line in f if line.strip()]
    assert len(ids) == 3000
    assert len(set(ids)) == 3000

    report = score_submission(
        str(TRAIN_DIR / "questions.jsonl"),
        str(TRAIN_DIR / "answers.jsonl"),
        str(out_path),
    )
    assert report.total_questions == 3000
```

`tests/answer_formatter/test_sc002_resume_after_interruption.py` (SC-002 — mô phỏng batch bị dừng
giữa chừng bằng `KeyboardInterrupt` ở `concurrency=1` để xác định được chính xác tại điểm nào bị
dừng, rồi chạy lại):

```python
"""SC-002: dừng batch giữa chừng (mô phỏng Ctrl-C/kill bằng KeyboardInterrupt) rồi chạy lại —
xác nhận resume không gọi lại answer_fn cho câu đã xong, xem specs/005-answer-formatter/spec.md."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from answer_formatter.runner import run_batch

_N_QUESTIONS = 50
_INTERRUPT_AT = 25


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_resume_after_simulated_interruption_completes_remaining_only(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": f"q{i}", "business_id": f"biz_{i}", "question": "a", "as_of_date": "2026-01-01"}
        for i in range(_N_QUESTIONS)
    ])
    out_path = tmp_path / "submission.jsonl"
    call_count = {"n": 0}

    def interrupting_fn(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
        call_count["n"] += 1
        if call_count["n"] > _INTERRUPT_AT:
            raise KeyboardInterrupt("giả lập bị dừng (Ctrl-C/kill)")
        return {"type": "string", "answer": business_id}

    with pytest.raises(KeyboardInterrupt):
        run_batch(questions_path, tmp_path, out_path, concurrency=1, answer_fn=interrupting_fn)

    rows_after_interrupt = _read_jsonl(out_path)
    assert len(rows_after_interrupt) == _INTERRUPT_AT

    def resuming_fn(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
        return {"type": "string", "answer": business_id}

    summary = run_batch(questions_path, tmp_path, out_path, concurrency=1, answer_fn=resuming_fn)

    assert summary.resumed_skipped == _INTERRUPT_AT
    assert summary.processed == _N_QUESTIONS - _INTERRUPT_AT

    final_rows = _read_jsonl(out_path)
    assert len({r["id"] for r in final_rows}) == _N_QUESTIONS
```

`tests/answer_formatter/test_sc004_real_integration.py` (SC-004 — `skipif` theo env var, giống
`test_baseline_golden.py` của 004):

```python
"""SC-004: 1 lượt chạy thật (không giả) trên 10 câu thật qua answer_question thật — cần model
server OpenAI-compatible THẬT đang chạy (set REASONING_AGENT_MODEL + REASONING_AGENT_BASE_URL),
xem specs/005-answer-formatter/spec.md."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from answer_formatter.runner import run_batch
from eval_harness.scoring import score_submission

from .conftest import TRAIN_DIR, build_real_dataset

_SAMPLE_SIZE = 10


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


@pytest.mark.skipif(
    not os.environ.get("REASONING_AGENT_MODEL") or not os.environ.get("REASONING_AGENT_BASE_URL"),
    reason="Cần REASONING_AGENT_MODEL + REASONING_AGENT_BASE_URL trỏ tới 1 model server thật đang chạy",
)
def test_real_batch_run_on_10_real_questions(tmp_path: Path):
    questions = _load_jsonl(TRAIN_DIR / "questions.jsonl")[:_SAMPLE_SIZE]
    answers = _load_jsonl(TRAIN_DIR / "answers.jsonl")
    answers_by_id = {a["id"]: a for a in answers}
    business_ids = {q["business_id"] for q in questions}

    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    build_real_dataset(dataset_dir, business_ids)

    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, questions)
    sample_answers_path = tmp_path / "answers.jsonl"
    _write_jsonl(sample_answers_path, [answers_by_id[q["id"]] for q in questions])

    out_path = tmp_path / "submission.jsonl"
    summary = run_batch(questions_path, dataset_dir, out_path)

    assert summary.processed == _SAMPLE_SIZE
    report = score_submission(str(questions_path), str(sample_answers_path), str(out_path))
    assert report.total_questions == _SAMPLE_SIZE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/answer_formatter/test_full_scale_fake.py tests/answer_formatter/test_sc002_resume_after_interruption.py tests/answer_formatter/test_sc004_real_integration.py -v`
Expected: `test_full_scale_fake.py` FAIL với `ModuleNotFoundError: No module named 'data_loader'`
hoặc lỗi import tương tự TRƯỚC khi file `conftest.py` được tạo (vì file test import từ
`.conftest`); sau khi tạo `conftest.py` ở Step 1, cả 2 file phải IMPORT được — nhưng
`test_full_scale_fake.py` vẫn FAIL thật nếu chạy trước khi mọi Task 1-4 hoàn tất (không áp dụng ở
đây vì đây là task cuối, chạy sau khi code đã có) — nếu `conftest.py`/`run_batch` đã đúng,
`test_full_scale_fake.py` sẽ PASS ngay (không có code sản phẩm mới để "fail" trước); bỏ qua bước
RED hình thức cho 2 file test này, chuyển thẳng Step 4 verify PASS.
`test_sc004_real_integration.py` SKIP nếu chưa có `REASONING_AGENT_MODEL`/`REASONING_AGENT_BASE_URL`
— đây là kỳ vọng đúng (không phải fail).

- [ ] **Step 3: (không có — không có code sản phẩm mới ở task này, xem Interfaces)**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/answer_formatter/test_full_scale_fake.py tests/answer_formatter/test_sc002_resume_after_interruption.py -v`
Expected: PASS (2 test — SC-001 chạy 3000 câu với `answer_fn` giả trong vài giây không gọi LLM;
SC-002 mô phỏng dừng giữa chừng rồi resume).

Nếu có model server thật đang chạy (export `REASONING_AGENT_MODEL` + `REASONING_AGENT_BASE_URL`
trước khi gọi pytest), chạy thêm:

Run: `pytest tests/answer_formatter/test_sc004_real_integration.py -v`
Expected: PASS (1 test, chậm — gọi LLM thật 10 lần) hoặc SKIPPED nếu chưa set env var.

Cuối cùng chạy toàn bộ test suite của 005 để xác nhận không có gì hỏng lẫn nhau:

Run: `pytest tests/answer_formatter/ -v`
Expected: PASS toàn bộ (trừ `test_sc004_real_integration.py` có thể SKIPPED nếu không có model
server).

- [ ] **Step 5: Commit**

```bash
git add tests/answer_formatter/conftest.py tests/answer_formatter/test_full_scale_fake.py tests/answer_formatter/test_sc002_resume_after_interruption.py tests/answer_formatter/test_sc004_real_integration.py
git commit -m "test: verify 005 at real dataset scale, resume after interruption, and against a real model (SC-001/002/004)"
```
