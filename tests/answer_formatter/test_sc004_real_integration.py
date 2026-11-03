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
