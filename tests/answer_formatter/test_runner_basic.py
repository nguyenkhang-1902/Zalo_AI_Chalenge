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


def test_negative_limit_raises(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [])
    out_path = tmp_path / "submission.jsonl"

    with pytest.raises(ValueError, match="limit"):
        run_batch(questions_path, tmp_path, out_path, limit=-1, answer_fn=_fake_answer_fn)


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


def test_malformed_as_of_date_written_as_unanswerable_and_batch_continues(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _write_jsonl(questions_path, [
        {"id": "q1", "business_id": "biz_1", "question": "a", "as_of_date": "khong-phai-ngay"},
        {"id": "q2", "business_id": "biz_2", "question": "b", "as_of_date": "2026-01-01"},
    ])
    out_path = tmp_path / "submission.jsonl"

    summary = run_batch(questions_path, tmp_path, out_path, answer_fn=_fake_answer_fn)

    rows = {r["id"]: r for r in _read_jsonl(out_path)}
    assert rows["q1"]["type"] == "unanswerable"
    assert rows["q2"]["type"] == "string"
    assert summary.errored == 1
    assert summary.processed == 2
