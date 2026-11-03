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
