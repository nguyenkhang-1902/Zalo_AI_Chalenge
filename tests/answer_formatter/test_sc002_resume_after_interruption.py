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
