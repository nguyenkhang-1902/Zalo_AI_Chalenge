import json

import pytest

from accuracy_boost.fewshot import FewShotPool


def _train_dir(tmp_path):
    rows = [
        ("q1", "Doanh thu tháng này là bao nhiêu?", "number"),
        ("q2", "Doanh thu tháng này so với tháng trước tăng giảm bao nhiêu %?", "percent"),
        ("q3", "Top 3 món bán chạy nhất tuần trước", "list"),
        ("q4", "Còn ai nợ tiền chưa trả?", "table"),
    ]
    (tmp_path / "questions.jsonl").write_text(
        "".join(json.dumps({"id": i, "business_id": "b", "question": q, "as_of_date": "2026-01-01"}, ensure_ascii=False) + "\n" for i, q, _ in rows),
        encoding="utf-8",
    )
    (tmp_path / "answers.jsonl").write_text(
        "".join(json.dumps({"id": i, "type": t, "answer": 1, "alias": []}) + "\n" for i, _, t in rows),
        encoding="utf-8",
    )
    return tmp_path


def test_selects_most_similar_ignoring_accents_and_case(tmp_path):
    pool = FewShotPool.from_train_dir(_train_dir(tmp_path))
    top = pool.select("doanh thu thang nay bao nhieu", k=1)
    assert top == [{"question": "Doanh thu tháng này là bao nhiêu?", "type": "number"}]


def test_excludes_identical_and_listed_questions(tmp_path):
    pool = FewShotPool.from_train_dir(_train_dir(tmp_path))
    question = "Doanh thu tháng này là bao nhiêu?"
    picked = pool.select(question, k=2, exclude_questions=frozenset({"Top 3 món bán chạy nhất tuần trước"}))
    texts = [p["question"] for p in picked]
    assert question not in texts
    assert "Top 3 món bán chạy nhất tuần trước" not in texts


def test_format_prompt_lists_type_only(tmp_path):
    pool = FewShotPool.from_train_dir(_train_dir(tmp_path))
    text = pool.format_prompt("Doanh thu tuần này?", k=2)
    assert "type=" in text and "đáp án" not in text.split("\n", 1)[1]
    assert FewShotPool([]).format_prompt("x", k=2) == ""


def test_requires_answers_file(tmp_path):
    (tmp_path / "questions.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="answers.jsonl"):
        FewShotPool.from_train_dir(tmp_path)
