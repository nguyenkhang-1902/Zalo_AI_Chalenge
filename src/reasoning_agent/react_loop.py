"""Vòng ReAct — FR-005/FR-006. Phần ToolSpec tạo ở Task 2 để date_tools/sql_tool/schema_tools
dùng được; run_react_loop + submit_answer thêm ở Task 5."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    schema: dict
    handler: Callable[..., dict]


MAX_TOOL_CALLS = 6
TIME_BUDGET_SECONDS = float(os.environ.get("REASONING_AGENT_TIME_BUDGET", "45"))

_VALID_TYPES = {"number", "percent", "date", "boolean", "string", "list", "table", "unanswerable"}
BUDGET_EXHAUSTED_REASON = "hết ngân sách bước suy luận"
_BUDGET_EXHAUSTED_RESULT = {"type": "unanswerable", "reason": BUDGET_EXHAUSTED_REASON}


def _submit_answer_tool_spec() -> ToolSpec:
    def handler(type: str, answer_json: str = "null", reason: str | None = None) -> dict:
        if type not in _VALID_TYPES:
            raise ValueError(f"type không hợp lệ: {type!r}, phải là 1 trong {sorted(_VALID_TYPES)}")
        if type == "unanswerable":
            return {"type": "unanswerable", "reason": reason or ""}
        return {"type": type, "answer": json.loads(answer_json)}

    return ToolSpec(
        schema={
            "name": "submit_answer",
            "description": "Đưa đáp án cuối cùng và kết thúc. PHẢI gọi tool này để trả lời.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": sorted(_VALID_TYPES)},
                    "answer_json": {
                        "type": "string",
                        "description": 'Giá trị đáp án, JSON-encode thành chuỗi (vd "4820000", "[1,2]")',
                    },
                    "reason": {"type": "string", "description": "Chỉ dùng khi type=unanswerable"},
                },
                "required": ["type"],
            },
        },
        handler=handler,
    )


def _dispatch(name: str, raw_arguments: str, registry: dict[str, ToolSpec]) -> dict:
    spec = registry.get(name)
    if spec is None:
        return {"error": f"tool không tồn tại: {name}"}
    try:
        kwargs = json.loads(raw_arguments) if raw_arguments else {}
        return spec.handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


def run_react_loop(
    chat_fn: Callable[[list[dict], list[dict], float], dict],
    system_prompt: str,
    question: str,
    tool_registry: dict[str, ToolSpec],
) -> dict[str, Any]:
    registry = {**tool_registry, "submit_answer": _submit_answer_tool_spec()}
    tools_payload = [{"type": "function", "function": spec.schema} for spec in registry.values()]

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    tool_calls_used = 0
    start = time.monotonic()

    while True:
        remaining = TIME_BUDGET_SECONDS - (time.monotonic() - start)
        if remaining <= 0 or tool_calls_used >= MAX_TOOL_CALLS:
            return dict(_BUDGET_EXHAUSTED_RESULT)

        try:
            response = chat_fn(messages, tools_payload, remaining)
        except Exception:
            return dict(_BUDGET_EXHAUSTED_RESULT)

        raw_tool_calls = response.get("tool_calls") or []
        if not raw_tool_calls:
            messages.append({"role": "assistant", "content": response.get("content")})
            messages.append(
                {
                    "role": "user",
                    "content": "Bạn phải gọi tool submit_answer để đưa đáp án cuối cùng, không trả lời bằng văn bản thường.",
                }
            )
            continue

        messages.append(
            {
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": [
                    {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in raw_tool_calls
                ],
            }
        )

        for tool_call in raw_tool_calls:
            if tool_calls_used >= MAX_TOOL_CALLS:
                return dict(_BUDGET_EXHAUSTED_RESULT)
            tool_calls_used += 1

            result = _dispatch(tool_call["name"], tool_call["arguments"], registry)

            if tool_call["name"] == "submit_answer" and "error" not in result:
                return result

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )
