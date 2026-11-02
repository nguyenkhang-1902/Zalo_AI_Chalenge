"""Tool run_sql — FR-003, chạy trên DuckDB READ-ONLY, tự bắt lỗi DuckDB (yêu cầu rõ của FR-003:
'trả lỗi DuckDB nguyên văn, không raise')."""
from __future__ import annotations

import duckdb

from reasoning_agent.react_loop import ToolSpec


def build_sql_tool(conn: duckdb.DuckDBPyConnection) -> ToolSpec:
    def run_sql(query: str) -> dict:
        try:
            result = conn.execute(query)
            columns = [d[0] for d in result.description]
            rows = [list(row) for row in result.fetchall()]
            return {"columns": columns, "rows": rows}
        except Exception as e:
            return {"error": str(e)}

    return ToolSpec(
        schema={
            "name": "run_sql",
            "description": "Chạy 1 câu SELECT trên DuckDB của business này, trả về columns + rows.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Câu lệnh SQL SELECT"}},
                "required": ["query"],
            },
        },
        handler=run_sql,
    )
