"""Cấu trúc dữ liệu dùng chung xuyên suốt pipeline data-loader."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class LoadedTable:
    source_files: list[str]
    sheet_name: str | None
    table_name: str
    header_confidence: str  # "high" | "low"
    frame: pd.DataFrame
    column_dtypes: dict = field(default_factory=dict)  # {"col": "numeric"|"date"|"text"|"raw"}
