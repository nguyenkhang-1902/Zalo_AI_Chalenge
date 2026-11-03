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
