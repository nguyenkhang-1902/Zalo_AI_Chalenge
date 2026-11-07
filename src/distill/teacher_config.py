"""Config teacher LLM cho distillation — đọc TEACHER_* env, reuse AgentConfig của reasoning_agent.
Teacher CHỈ dùng lúc sinh data (offline), KHÔNG vào Docker nộp (FR-011)."""
from __future__ import annotations

import os

from reasoning_agent.config import AgentConfig


def load_teacher_config() -> AgentConfig:
    model = os.environ.get("TEACHER_MODEL", "").strip()
    base_url = os.environ.get("TEACHER_BASE_URL", "").strip()
    if not model:
        raise ValueError("Thiếu biến môi trường TEACHER_MODEL")
    if not base_url:
        raise ValueError("Thiếu biến môi trường TEACHER_BASE_URL")
    return AgentConfig(
        model=model,
        base_url=base_url.rstrip("/"),
        api_key=os.environ.get("TEACHER_API_KEY", ""),
    )
