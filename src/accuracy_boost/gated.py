"""Chạy N lần → đáp án đồng thuận hoặc abstain (US1). Run 0 greedy, run i≥1 lấy mẫu với seed
base+i (FR-010: tất định theo chỉ số lần chạy, không theo question_id)."""
from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Callable

from accuracy_boost.consensus import decide
from reasoning_agent import answer_question
from reasoning_agent.options import AgentOptions

logger = logging.getLogger(__name__)

ABSTAIN = {"type": "abstain"}


def options_for_run(base: AgentOptions, run_index: int, sample_temperature: float) -> AgentOptions:
    temperature = 0.0 if run_index == 0 else sample_temperature
    return replace(base, temperature=temperature, seed=base.seed + run_index)


def answer_with_gate(
    question: str,
    business_id: str,
    as_of_date: date,
    dataset_dir: Path,
    *,
    n_runs: int,
    threshold: float,
    sample_temperature: float,
    base_options: AgentOptions | None = None,
    run_fn: Callable[..., dict] = answer_question,
) -> dict:
    base = base_options or AgentOptions()
    results: list[dict] = []
    for run_index in range(n_runs):
        options = options_for_run(base, run_index, sample_temperature)
        try:
            results.append(run_fn(question, business_id, as_of_date, dataset_dir, options=options))
        except FileNotFoundError:
            raise
        except Exception as exc:  # noqa: BLE001 - 1 lần chạy lỗi chỉ là 1 phiếu abstain
            logger.warning("run %d failed, counted as abstain: %s", run_index, exc)
            results.append(dict(ABSTAIN))
    decision = decide(results, threshold)
    return decision.result if decision.result is not None else dict(ABSTAIN)


def make_gated_answer_fn(**kwargs) -> Callable[[str, str, date, Path], dict]:
    def answer_fn(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
        return answer_with_gate(question, business_id, as_of_date, dataset_dir, **kwargs)

    return answer_fn
