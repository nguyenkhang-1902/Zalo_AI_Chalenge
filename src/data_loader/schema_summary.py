"""Sinh bản tóm tắt schema (cột/kiểu/mẫu) cho mỗi table, để sub-project sau dùng xây prompt."""
from __future__ import annotations

from data_loader.models import LoadedTable

_SAMPLE_SIZE = 5


def summarize_table(table: LoadedTable) -> dict:
    frame = table.frame
    columns = []
    for col in frame.columns:
        series = frame[col]
        non_null = series.dropna()
        columns.append(
            {
                "name": col,
                "dtype": table.column_dtypes.get(col, "text"),
                "n_null": int(series.isna().sum()),
                "n_rows": int(len(series)),
                "sample_values": non_null.head(_SAMPLE_SIZE).tolist(),
            }
        )
    return {
        "table_name": table.table_name,
        "source_files": table.source_files,
        "header_confidence": table.header_confidence,
        "columns": columns,
    }


def summarize_business(business_id: str, tables: list[LoadedTable], readme_raw: str) -> dict:
    return {
        "business_id": business_id,
        "readme": readme_raw,
        "tables": [summarize_table(t) for t in tables],
    }
