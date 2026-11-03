"""Tuỳ chọn biến thể hoá 1 lần chạy answer_question (007) — mặc định giữ nguyên hành vi 004."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from reasoning_agent.llm_client import SEED, TEMPERATURE


@dataclass(frozen=True)
class AgentOptions:
    temperature: float = TEMPERATURE
    seed: int = SEED
    semantic_tools: bool = False
    prompt_extra_fn: Callable[[str], str] | None = None
