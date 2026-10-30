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
