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
