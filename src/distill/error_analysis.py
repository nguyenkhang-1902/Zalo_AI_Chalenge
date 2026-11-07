"""Phân loại kết quả dự đoán vs gold để so baseline vs fine-tuned (SC-003): correct / wrong_VALUE /
wrong_TYPE / abstain_model / abstain_budget / wrong_should_abstain. Reuse is_correct."""
from __future__ import annotations

from collections import Counter

from eval_harness.matchers import is_correct
from reasoning_agent.react_loop import BUDGET_EXHAUSTED_REASON


def classify_outcomes(predictions, answers_by_id) -> dict[str, int]:
    c: Counter = Counter()
    for p in predictions:
        g = answers_by_id[p["id"]]
        res = p["result"]
        pt = res.get("type")
        if is_correct(g["type"], res, g.get("answer"), g.get("alias", [])):
            c["correct"] += 1
        elif pt == "unanswerable":
            c["abstain_budget" if res.get("reason") == BUDGET_EXHAUSTED_REASON else "abstain_model"] += 1
        elif g["type"] == "unanswerable":
            c["wrong_should_abstain"] += 1
        elif pt != g["type"]:
            c["wrong_TYPE"] += 1
        else:
            c["wrong_VALUE"] += 1
    return dict(c)
