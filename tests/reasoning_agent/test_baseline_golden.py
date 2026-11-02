"""Task 7 — SC-001/SC-002: baseline thật trên 100 câu hỏi mẫu train/, cần model server
OpenAI-compatible THẬT đang chạy (set REASONING_AGENT_MODEL + REASONING_AGENT_BASE_URL)."""
from __future__ import annotations

import json
import os
import random
import shutil
import time
from datetime import date
from pathlib import Path

import pytest

from data_loader.build_business_db import build_business
from eval_harness.report import format_report
from eval_harness.scoring import score_submission
from reasoning_agent.agent import answer_question

from .conftest import TRAIN_DIR

_SAMPLE_SIZE = 100


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _stratified_sample(questions: list[dict], answers_by_id: dict, n: int) -> list[dict]:
    by_type: dict[str, list[dict]] = {}
    for q in questions:
        truth_type = answers_by_id[q["id"]]["type"]
        by_type.setdefault(truth_type, []).append(q)

    rng = random.Random(42)
    per_type = max(1, n // len(by_type))
    sampled: list[dict] = []
    for type_name in sorted(by_type):
        items = list(by_type[type_name])
        rng.shuffle(items)
        sampled.extend(items[:per_type])
    return sampled[:n]


@pytest.mark.skipif(
    not os.environ.get("REASONING_AGENT_MODEL") or not os.environ.get("REASONING_AGENT_BASE_URL"),
    reason="Cần REASONING_AGENT_MODEL + REASONING_AGENT_BASE_URL trỏ tới 1 model server thật đang chạy",
)
def test_baseline_accuracy_on_100_real_questions(tmp_path: Path):
    questions = _load_jsonl(TRAIN_DIR / "questions.jsonl")
    answers = _load_jsonl(TRAIN_DIR / "answers.jsonl")
    answers_by_id = {a["id"]: a for a in answers}

    sample = _stratified_sample(questions, answers_by_id, _SAMPLE_SIZE)
    business_ids = sorted({q["business_id"] for q in sample})

    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    shutil.copy(TRAIN_DIR / "rulebook.md", dataset_dir / "rulebook.md")
    shutil.copy(TRAIN_DIR / "calendar.csv", dataset_dir / "calendar.csv")
    for business_id in business_ids:
        build_business(TRAIN_DIR / "data" / business_id, dataset_dir)

    submission_path = tmp_path / "submission.jsonl"
    elapsed_per_question = []
    with submission_path.open("w", encoding="utf-8") as f:
        for q in sample:
            start = time.monotonic()
            result = answer_question(
                question=q["question"],
                business_id=q["business_id"],
                as_of_date=date.fromisoformat(q["as_of_date"]),
                dataset_dir=dataset_dir,
            )
            elapsed_per_question.append(time.monotonic() - start)
            f.write(json.dumps({"id": q["id"], **result}, ensure_ascii=False) + "\n")

    sample_questions_path = tmp_path / "sample_questions.jsonl"
    sample_answers_path = tmp_path / "sample_answers.jsonl"
    with sample_questions_path.open("w", encoding="utf-8") as f:
        for q in sample:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with sample_answers_path.open("w", encoding="utf-8") as f:
        for q in sample:
            f.write(json.dumps(answers_by_id[q["id"]], ensure_ascii=False) + "\n")

    report = score_submission(str(sample_questions_path), str(sample_answers_path), str(submission_path))
    print(format_report(report))

    assert all(e < 45.0 for e in elapsed_per_question), "Có câu vượt ngân sách 45s mà không rơi về unanswerable (SC-001)"
    assert report.accuracy > 0.0, "Baseline accuracy phải > 0% (SC-002)"

    avg_seconds = sum(elapsed_per_question) / len(elapsed_per_question)
    budget_per_question = (6 * 3600) / 1000  # SC-005: 6h / 1000 câu public_test, cận trên tạm tính
    print(f"Thời gian trung bình/câu: {avg_seconds:.1f}s (ngân sách tạm tính SC-005: {budget_per_question:.1f}s)")
