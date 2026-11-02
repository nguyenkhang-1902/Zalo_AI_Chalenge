"""HTTP client OpenAI-compatible chat-completions, model-agnostic (FR-007/FR-008) — tương thích
vLLM/Ollama/llama.cpp vì đều expose `/chat/completions` theo chuẩn OpenAI function-calling.
temperature/seed là HẰNG SỐ ở đây (không qua env) — FR-008 chỉ yêu cầu giá trị thấp/0 + cố định,
không yêu cầu cấu hình được; chỉ model/endpoint mới bắt buộc qua env (FR-007)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from reasoning_agent.config import AgentConfig

TEMPERATURE = 0.0
SEED = 42


class LLMClientError(Exception):
    """Mọi lỗi giao tiếp với model server (timeout, lỗi HTTP, JSON phản hồi hỏng)."""


def call_chat_completion(
    config: AgentConfig,
    messages: list[dict],
    tools: list[dict],
    timeout: float,
) -> dict:
    body = {
        "model": config.model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": TEMPERATURE,
        "seed": SEED,
    }
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    request = urllib.request.Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise LLMClientError(str(e)) from e

    try:
        message: dict[str, Any] = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMClientError(f"Phản hồi model server không đúng format: {payload!r}") from e

    raw_tool_calls = message.get("tool_calls") or []
    tool_calls = [
        {"id": tc["id"], "name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
        for tc in raw_tool_calls
    ]
    return {"content": message.get("content"), "tool_calls": tool_calls}
