"""Entry point FR-001 — wiring toàn bộ tool registry + system prompt + react loop cho 1 câu hỏi."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from date_resolver import load_calendar
from reasoning_agent.config import load_config
from reasoning_agent.date_tools import build_date_tool_registry
from reasoning_agent.llm_client import call_chat_completion
from reasoning_agent.prompt import build_system_prompt
from reasoning_agent.react_loop import run_react_loop
from reasoning_agent.schema_tools import build_schema_tools, load_schema
from reasoning_agent.sql_tool import build_sql_tool


def answer_question(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
    rulebook_path = dataset_dir / "rulebook.md"
    calendar_path = dataset_dir / "calendar.csv"
    if not rulebook_path.exists():
        raise FileNotFoundError(f"Thiếu rulebook.md trong {dataset_dir}")
    if not calendar_path.exists():
        raise FileNotFoundError(f"Thiếu calendar.csv trong {dataset_dir}")

    rulebook_text = rulebook_path.read_text(encoding="utf-8")
    calendar_index = load_calendar(str(calendar_path))
    schema = load_schema(dataset_dir, business_id)

    config = load_config()
    system_prompt = build_system_prompt(schema, rulebook_text)

    db_path = dataset_dir / f"{business_id}.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        registry = {
            **build_date_tool_registry(calendar_index, as_of_date),
            **build_schema_tools(schema),
            "run_sql": build_sql_tool(conn),
        }

        def chat_fn(messages: list[dict], tools: list[dict], timeout: float) -> dict:
            return call_chat_completion(config, messages, tools, timeout)

        return run_react_loop(chat_fn, system_prompt, question, registry)
    finally:
        conn.close()
