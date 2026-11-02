"""Vòng ReAct — FR-005/FR-006. Phần ToolSpec tạo ở Task 2 để date_tools/sql_tool/schema_tools
dùng được; run_react_loop + submit_answer thêm ở Task 5."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolSpec:
    schema: dict
    handler: Callable[..., dict]
