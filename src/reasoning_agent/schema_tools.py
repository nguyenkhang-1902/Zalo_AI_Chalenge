"""Tool đọc README/chi tiết table từ schema.json đã build sẵn — FR-002, FR-003."""
from __future__ import annotations

import json
from pathlib import Path

from reasoning_agent.react_loop import ToolSpec


def load_schema(dataset_dir: Path, business_id: str) -> dict:
    schema_path = dataset_dir / f"{business_id}.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def build_schema_tools(schema: dict) -> dict[str, ToolSpec]:
    tables_by_name = {t["table_name"]: t for t in schema["tables"]}

    def get_readme() -> dict:
        return {"readme": schema["readme"]}

    def get_table_detail(table_name: str) -> dict:
        table = tables_by_name.get(table_name)
        if table is None:
            raise ValueError(
                f"table không tồn tại: {table_name!r}. Các table có: {sorted(tables_by_name)}"
            )
        return {"table_name": table["table_name"], "columns": table["columns"]}

    return {
        "get_readme": ToolSpec(
            schema={
                "name": "get_readme",
                "description": "Đọc nguyên văn README.md của business này (quy ước dữ liệu, tên cột gốc).",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            handler=get_readme,
        ),
        "get_table_detail": ToolSpec(
            schema={
                "name": "get_table_detail",
                "description": "Đọc chi tiết đầy đủ 1 table: mọi cột kèm dtype, số dòng/null, mẫu giá trị thật.",
                "parameters": {
                    "type": "object",
                    "properties": {"table_name": {"type": "string"}},
                    "required": ["table_name"],
                },
            },
            handler=get_table_detail,
        ),
    }
