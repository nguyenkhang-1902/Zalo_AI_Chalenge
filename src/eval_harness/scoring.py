"""Đọc questions/answers/submission và chấm điểm — xem specs/003-eval-harness/spec.md."""
from __future__ import annotations

import json

from .matchers import is_correct
from .report import EvalReport, TypeBreakdown


def _load_jsonl(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_submission(path: str) -> tuple[dict, int]:
    submission: dict = {}
    malformed_count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                malformed_count += 1
                continue
            if not isinstance(row, dict):
                malformed_count += 1
                continue
            row_id = row.get("id")
            if not isinstance(row_id, str):
                malformed_count += 1
                continue
            if row_id in submission:
                raise ValueError(f"id trùng lặp trong submission: {row_id}")
            submission[row_id] = row
    return submission, malformed_count


def score_submission(questions_path: str, answers_path: str, submission_path: str) -> EvalReport:
    questions = _load_jsonl(questions_path)
    answers = _load_jsonl(answers_path)
    submission, malformed_count = _load_submission(submission_path)

    answers_by_id = {a["id"]: a for a in answers}
    for q in questions:
        if q["id"] not in answers_by_id:
            raise ValueError(f"answers.jsonl thiếu entry cho id: {q['id']}")

    extra_ids_ignored = sum(1 for sid in submission if sid not in answers_by_id)

    by_type: dict = {}
    by_business: dict = {}
    total_score = 0
    correct = incorrect = abstained = 0

    for q in questions:
        qid = q["id"]
        truth = answers_by_id[qid]
        truth_type = truth["type"]
        business_id = q["business_id"]

        pred = submission.get(qid)
        if pred is None or pred.get("type") == "abstain":
            points = 0
            outcome = "abstained"
        elif is_correct(truth_type, pred, truth.get("answer"), truth.get("alias")):
            points = 1
            outcome = "correct"
        else:
            points = -1
            outcome = "incorrect"

        total_score += points
        if outcome == "correct":
            correct += 1
        elif outcome == "incorrect":
            incorrect += 1
        else:
            abstained += 1

        by_type.setdefault(truth_type, TypeBreakdown()).record(outcome)
        by_business.setdefault(business_id, TypeBreakdown()).record(outcome)

    total_questions = len(questions)
    accuracy = correct / total_questions if total_questions else 0.0

    return EvalReport(
        total_score=total_score,
        total_questions=total_questions,
        correct=correct,
        incorrect=incorrect,
        abstained=abstained,
        accuracy=accuracy,
        by_type=by_type,
        by_business=by_business,
        malformed_count=malformed_count,
        extra_ids_ignored=extra_ids_ignored,
    )
