"""Sinh trace ReAct bằng teacher, GHI lại mảng messages — mirror answer_question (004) nhưng bọc
chat_fn để bắt trace, KHÔNG sửa lõi react_loop/agent. messages là cùng 1 list object mà
run_react_loop bồi đắp, nên sau khi loop xong nó đã chứa cả assistant-turn submit_answer cuối."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

import duckdb

from date_resolver import load_calendar
from reasoning_agent.config import AgentConfig
from reasoning_agent.date_tools import build_date_tool_registry
from reasoning_agent.llm_client import call_chat_completion
from reasoning_agent.prompt import build_system_prompt
from reasoning_agent.react_loop import run_react_loop
from reasoning_agent.schema_tools import build_schema_tools, load_schema
from reasoning_agent.sql_tool import build_sql_tool


@dataclass
class TraceResult:
    result: dict
    messages: list[dict]
    tools: list[dict] = field(default_factory=list)  # tool-definitions (gồm schema_tools) để train khớp inference


def generate_trace(
    question: str,
    business_id: str,
    as_of_date: date,
    dataset_dir: Path,
    teacher_config: AgentConfig,
    temperature: float = 0.0,
    seed: int = 42,
    chat_completion_fn: Callable = call_chat_completion,
) -> TraceResult:
    rulebook_text = (dataset_dir / "rulebook.md").read_text(encoding="utf-8")
    calendar_index = load_calendar(str(dataset_dir / "calendar.csv"))
    schema = load_schema(dataset_dir, business_id)
    system_prompt = build_system_prompt(schema, rulebook_text, "")

    conn = duckdb.connect(str(dataset_dir / f"{business_id}.duckdb"), read_only=True)
    try:
        registry = {
            **build_date_tool_registry(calendar_index, as_of_date),
            **build_schema_tools(schema),
            "run_sql": build_sql_tool(conn),
        }
        captured: dict = {}

        def recording_chat_fn(messages: list[dict], tools: list[dict], timeout: float) -> dict:
            captured["messages"] = messages
            captured["tools"] = tools  # cùng payload mỗi lần; run_react_loop đã gộp cả submit_answer
            return chat_completion_fn(
                teacher_config, messages, tools, timeout, temperature=temperature, seed=seed
            )

        result = run_react_loop(recording_chat_fn, system_prompt, question, registry)
        return TraceResult(
            result=result,
            messages=copy.deepcopy(captured.get("messages", [])),
            tools=copy.deepcopy(captured.get("tools", [])),
        )
    finally:
        conn.close()
