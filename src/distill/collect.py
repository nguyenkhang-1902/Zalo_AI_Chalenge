"""Rejection sampling: thử tối đa max_attempts lần, GIỮ trace đầu tiên có đáp án khớp gold qua
eval_harness.is_correct (reuse). Lần 0 greedy, các lần sau temperature cao hơn + seed khác."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

from eval_harness.matchers import is_correct
from reasoning_agent.config import AgentConfig
from reasoning_agent.llm_client import call_chat_completion

from distill.trace_generator import TraceResult, generate_trace


def collect_verified_trace(
    question: str,
    business_id: str,
    as_of_date: date,
    dataset_dir: Path,
    teacher_config: AgentConfig,
    truth_type: str,
    truth_answer,
    alias: list,
    max_attempts: int = 3,
    base_seed: int = 42,
    generate_fn: Callable = generate_trace,
    chat_completion_fn: Callable = call_chat_completion,
) -> TraceResult | None:
    for i in range(max_attempts):
        trace = generate_fn(
            question,
            business_id,
            as_of_date,
            dataset_dir,
            teacher_config,
            temperature=0.0 if i == 0 else 0.7,
            seed=base_seed + i,
            chat_completion_fn=chat_completion_fn,
        )
        if is_correct(truth_type, trace.result, truth_answer, alias):
            return trace
    return None
