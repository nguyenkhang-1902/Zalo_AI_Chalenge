import json
from pathlib import Path

import pytest

from eval_harness.scoring import score_submission

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAIN_QUESTIONS = REPO_ROOT / "train" / "questions.jsonl"
TRAIN_ANSWERS = REPO_ROOT / "train" / "answers.jsonl"


def _write_submission(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_answers_as_submission_rows() -> list[dict]:
    rows = []
    with open(TRAIN_ANSWERS, encoding="utf-8") as f:
        for line in f:
            a = json.loads(line)
            rows.append({"id": a["id"], "type": a["type"], "answer": a["answer"]})
    return rows


def test_perfect_submission_scores_100_percent_on_real_train_set(tmp_path):
    rows = _load_answers_as_submission_rows()
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.total_questions == 3000
    assert report.correct == 3000
    assert report.incorrect == 0
    assert report.abstained == 0
    assert report.accuracy == 1.0
    assert report.total_score == 3000


def test_wrong_submission_loses_2_points_per_wrong_question(tmp_path):
    rows = _load_answers_as_submission_rows()
    # Sửa sai 5 câu number đầu tiên: cộng thêm 1 vào giá trị đúng
    wrong_count = 0
    for row in rows:
        if row["type"] == "number" and wrong_count < 5:
            row["answer"] = row["answer"] + 1
            wrong_count += 1
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.incorrect == 5
    assert report.correct == 2995
    assert report.total_score == 3000 - 2 * 5


def test_missing_id_in_submission_scores_zero_not_negative(tmp_path):
    rows = _load_answers_as_submission_rows()[3:]  # bỏ qua 3 câu đầu
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.abstained == 3
    assert report.correct == 2997
    assert report.total_score == 2997


def test_explicit_abstain_scores_zero(tmp_path):
    rows = _load_answers_as_submission_rows()
    rows[0] = {"id": rows[0]["id"], "type": "abstain"}
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.abstained == 1
    assert report.correct == 2999


def test_non_string_reason_scores_zero_even_if_otherwise_correct(tmp_path):
    rows = _load_answers_as_submission_rows()
    rows[0]["reason"] = 123  # reason không phải chuỗi, dù answer đúng
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.abstained == 1
    assert report.correct == 2999


def test_unanswerable_with_non_string_reason_scores_zero(tmp_path):
    rows = _load_answers_as_submission_rows()
    for row in rows:
        if row["type"] == "unanswerable":
            row["reason"] = None
            break
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.abstained == 1


def test_malformed_json_line_scores_zero_without_crashing(tmp_path):
    rows = _load_answers_as_submission_rows()
    submission_path = tmp_path / "submission.jsonl"
    with open(submission_path, "w", encoding="utf-8") as f:
        f.write("{not valid json\n")
        for row in rows[1:]:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.malformed_count == 1
    assert report.abstained == 1
    assert report.correct == 2999


def test_json_valid_but_not_object_scores_zero_without_crashing(tmp_path):
    rows = _load_answers_as_submission_rows()
    submission_path = tmp_path / "submission.jsonl"
    with open(submission_path, "w", encoding="utf-8") as f:
        f.write("[1, 2, 3]\n")
        for row in rows[1:]:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.malformed_count == 1
    assert report.abstained == 1
    assert report.correct == 2999


def test_duplicate_id_in_submission_raises_value_error(tmp_path):
    rows = _load_answers_as_submission_rows()[:2]
    rows.append(rows[0])  # id trùng
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    with pytest.raises(ValueError):
        score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))


def test_breakdown_by_type_and_business_sum_to_total(tmp_path):
    rows = _load_answers_as_submission_rows()
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert sum(bd.total for bd in report.by_type.values()) == 3000
    assert sum(bd.total for bd in report.by_business.values()) == 3000
    assert set(report.by_type.keys()) == {
        "number", "percent", "date", "boolean", "string", "list", "table", "unanswerable",
    }


def test_answers_missing_entry_for_question_raises_value_error(tmp_path):
    questions_path = tmp_path / "questions.jsonl"
    answers_path = tmp_path / "answers.jsonl"
    submission_path = tmp_path / "submission.jsonl"

    with open(questions_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"id": "q_x", "business_id": "biz_x", "question": "?", "as_of_date": "2026-01-01"}) + "\n")
    with open(answers_path, "w", encoding="utf-8") as f:
        pass  # rỗng — thiếu entry cho q_x
    with open(submission_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"id": "q_x", "type": "number", "answer": 1}) + "\n")

    with pytest.raises(ValueError):
        score_submission(str(questions_path), str(answers_path), str(submission_path))
