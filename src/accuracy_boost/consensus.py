"""Bỏ phiếu giữa N lần chạy → đáp án hoặc abstain (US1) + đường cong PA theo ngưỡng (FR-002).

Phiếu "hết ngân sách" của 004 là abstain chứ không phải unanswerable: với PA, trả unanswerable
sai tốn -1."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass

from answer_formatter.normalize import normalize_answer
from eval_harness.matchers import is_correct
from reasoning_agent.react_loop import BUDGET_EXHAUSTED_REASON

ABSTAIN_KEY = "abstain"


@dataclass(frozen=True)
class Decision:
    result: dict | None
    agreement: float


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def answer_key(result: dict) -> str:
    result_type = result.get("type")
    if result_type == "abstain":
        return ABSTAIN_KEY
    if result_type == "unanswerable":
        return ABSTAIN_KEY if result.get("reason") == BUDGET_EXHAUSTED_REASON else "unanswerable"

    answer = result.get("answer")
    if result_type in ("number", "percent") and _is_number(answer):
        return f"{result_type}:{round(float(answer), 2)}"
    if result_type == "string" and isinstance(answer, str):
        return f"string:{' '.join(answer.lower().split())}"
    if result_type == "table" and isinstance(answer, dict):
        rows = sorted(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in answer.get("rows") or [])
        return "table:" + json.dumps({"columns": answer.get("columns"), "rows": rows}, ensure_ascii=False)
    return f"{result_type}:" + json.dumps(answer, ensure_ascii=False, sort_keys=True, default=str)


def decide(results: list[dict], threshold: float) -> Decision:
    if not results:
        raise ValueError("decide cần ít nhất 1 kết quả")
    results = [normalize_answer(r) for r in results]  # đúng thứ runner ghi vào submission
    keys = [answer_key(r) for r in results]
    counts = Counter(k for k in keys if k != ABSTAIN_KEY)
    if not counts:
        return Decision(None, 0.0)

    best = max(counts.values())
    winner_key = next(k for k in keys if counts.get(k) == best)
    agreement = best / len(results)
    if agreement + 1e-9 < threshold:
        return Decision(None, agreement)
    return Decision(results[keys.index(winner_key)], agreement)


def pa_curve(
    runs_by_id: dict[str, list[dict]], answers_by_id: dict[str, dict], thresholds: list[float]
) -> list[dict]:
    rows = []
    for threshold in thresholds:
        correct = wrong = abstained = 0
        for question_id, results in runs_by_id.items():
            decision = decide(results, threshold)
            if decision.result is None:
                abstained += 1
                continue
            truth = answers_by_id[question_id]
            if is_correct(truth["type"], decision.result, truth.get("answer"), truth.get("alias")):
                correct += 1
            else:
                wrong += 1
        total = len(runs_by_id)
        rows.append(
            {
                "threshold": threshold,
                "pa": (correct - wrong) / total if total else 0.0,
                "correct": correct,
                "wrong": wrong,
                "abstained": abstained,
            }
        )
    return rows
