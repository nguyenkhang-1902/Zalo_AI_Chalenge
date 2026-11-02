"""Đọc model LLM đích qua env var — FR-007: tên/endpoint model KHÔNG hard-code ở bất kỳ đâu khác
trong source (SC-003 grep phải sạch)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    model: str
    base_url: str
    api_key: str


def load_config() -> AgentConfig:
    model = os.environ.get("REASONING_AGENT_MODEL", "").strip()
    base_url = os.environ.get("REASONING_AGENT_BASE_URL", "").strip()
    if not model:
        raise ValueError("Thiếu biến môi trường REASONING_AGENT_MODEL")
    if not base_url:
        raise ValueError("Thiếu biến môi trường REASONING_AGENT_BASE_URL")
    api_key = os.environ.get("REASONING_AGENT_API_KEY", "")
    return AgentConfig(model=model, base_url=base_url.rstrip("/"), api_key=api_key)
