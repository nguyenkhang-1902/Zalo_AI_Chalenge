"""So khớp giá trị dự đoán với ground truth theo rulebook.md §9 — xem specs/003-eval-harness/spec.md."""
from __future__ import annotations

import re

NUMBER_EPSILON = 1e-6


def _normalize_string(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s


def match_number(predicted, truth) -> bool:
    if isinstance(predicted, bool) or isinstance(truth, bool):
        return False
    if not isinstance(predicted, (int, float)) or not isinstance(truth, (int, float)):
        return False
    return abs(predicted - truth) < NUMBER_EPSILON


def match_percent(predicted, truth) -> bool:
    return match_number(predicted, truth)


def match_date(predicted, truth) -> bool:
    return isinstance(predicted, str) and isinstance(truth, str) and predicted == truth


def match_boolean(predicted, truth) -> bool:
    return isinstance(predicted, bool) and isinstance(truth, bool) and predicted == truth


def match_string(predicted, truth: str, alias: list[str]) -> bool:
    if not isinstance(predicted, str):
        return False
    normalized_predicted = _normalize_string(predicted)
    candidates = [truth, *(alias or [])]
    return any(
        isinstance(c, str) and normalized_predicted == _normalize_string(c) for c in candidates
    )


def match_list(predicted, truth: list, alias: list) -> bool:
    if not isinstance(predicted, list) or len(predicted) != len(truth):
        return False
    alias = alias or [[] for _ in truth]
    for i, truth_val in enumerate(truth):
        pred_val = predicted[i]
        elem_alias = alias[i] if i < len(alias) else []
        if isinstance(truth_val, str):
            if not match_string(pred_val, truth_val, elem_alias):
                return False
        elif isinstance(truth_val, (int, float)) and not isinstance(truth_val, bool):
            if not match_number(pred_val, truth_val):
                return False
        else:
            if pred_val != truth_val:
                return False
    return True


def _column_index_map(pred_columns: list, truth_columns: list) -> list | None:
    if len(pred_columns) == len(truth_columns) and set(pred_columns) == set(truth_columns):
        return [pred_columns.index(c) for c in truth_columns]
    return None


def _row_matches(pred_row: list, truth_row: list, row_alias: list) -> bool:
    if not match_string(pred_row[0], truth_row[0], row_alias):
        return False
    for i in range(1, len(truth_row)):
        if not match_number(pred_row[i], truth_row[i]):
            return False
    return True


def match_table(predicted, truth: dict, alias: list) -> bool:
    if not isinstance(predicted, dict):
        return False
    pred_columns = predicted.get("columns")
    pred_rows = predicted.get("rows")
    if not isinstance(pred_columns, list) or not isinstance(pred_rows, list):
        return False

    truth_columns = truth["columns"]
    truth_rows = truth["rows"]
    if len(pred_columns) != len(truth_columns) or len(pred_rows) != len(truth_rows):
        return False

    index_map = _column_index_map(pred_columns, truth_columns)
    if index_map is None:
        index_map = list(range(len(truth_columns)))

    reordered_pred_rows = []
    for row in pred_rows:
        if not isinstance(row, list) or len(row) != len(truth_columns):
            return False
        reordered_pred_rows.append([row[i] for i in index_map])

    alias = alias or [[] for _ in truth_rows]
    used = [False] * len(reordered_pred_rows)
    for t_idx, truth_row in enumerate(truth_rows):
        row_alias = alias[t_idx] if t_idx < len(alias) else []
        matched = False
        for p_idx, pred_row in enumerate(reordered_pred_rows):
            if used[p_idx]:
                continue
            if _row_matches(pred_row, truth_row, row_alias):
                used[p_idx] = True
                matched = True
                break
        if not matched:
            return False
    return True


def match_unanswerable(predicted_type: str) -> bool:
    return predicted_type == "unanswerable"


def is_correct(truth_type: str, predicted: dict, truth_answer, alias: list) -> bool:
    if not isinstance(predicted, dict):
        return False
    if predicted.get("type") != truth_type:
        return False
    if truth_type == "unanswerable":
        return True

    predicted_answer = predicted.get("answer")
    if truth_type == "number":
        return match_number(predicted_answer, truth_answer)
    if truth_type == "percent":
        return match_percent(predicted_answer, truth_answer)
    if truth_type == "date":
        return match_date(predicted_answer, truth_answer)
    if truth_type == "boolean":
        return match_boolean(predicted_answer, truth_answer)
    if truth_type == "string":
        return match_string(predicted_answer, truth_answer, alias)
    if truth_type == "list":
        return match_list(predicted_answer, truth_answer, alias)
    if truth_type == "table":
        return match_table(predicted_answer, truth_answer, alias)
    return False
