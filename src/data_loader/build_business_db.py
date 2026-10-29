"""Orchestrator: README -> header locate -> clean -> group -> DuckDB + schema summary, 1 business."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from data_loader.duckdb_writer import write_tables
from data_loader.header_locator import locate_header
from data_loader.models import LoadedTable
from data_loader.readme_parser import ReadmeInfo, columns_for, parse_readme
from data_loader.schema_grouping import group_same_schema_files
from data_loader.schema_summary import summarize_business
from data_loader.sheet_reader import RawSheet, read_all_sheets
from data_loader.value_cleaner import (
    clean_numeric_column,
    parse_vn_date_column,
    split_quantity_unit,
)

logger = logging.getLogger(__name__)


def _build_header(header_row: tuple) -> list[str]:
    """Tên cột từ dòng header thô, đổi tên None -> col_i và chống trùng tên (vd 'Ghi chú' x2)."""
    seen: dict[str, int] = {}
    header: list[str] = []
    for i, c in enumerate(header_row):
        name = str(c).strip() if c is not None else f"col_{i}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        header.append(name)
    return header


def _clean_sheet_to_table(raw_sheet: RawSheet, expected_columns: list[str] | None) -> LoadedTable | None:
    match = locate_header(raw_sheet.rows, expected_columns)
    header_row = raw_sheet.rows[match.header_row_index]
    data_rows = raw_sheet.rows[match.header_row_index + 1 :]
    if not data_rows:
        return None

    header = _build_header(header_row)
    frame = pd.DataFrame(data_rows, columns=header)
    column_dtypes: dict[str, str] = {}

    for col in list(frame.columns):
        values = frame[col].tolist()

        split = split_quantity_unit(values)
        if split is not None:
            numbers, units = split
            frame[col] = numbers
            frame[f"{col} (đơn vị)"] = units
            column_dtypes[col] = "numeric"
            column_dtypes[f"{col} (đơn vị)"] = "text"
            continue

        cleaned, dtype = clean_numeric_column(values)
        if dtype == "numeric":
            frame[col] = cleaned
            column_dtypes[col] = "numeric"
            continue

        cleaned, dtype = parse_vn_date_column(values)
        if dtype == "date":
            frame[col] = cleaned
            column_dtypes[col] = "date"
        else:
            column_dtypes[col] = "raw"

    table_name = raw_sheet.source_file.rsplit(".", 1)[0]
    if raw_sheet.sheet_name:
        table_name = f"{table_name}__{raw_sheet.sheet_name}"

    return LoadedTable(
        source_files=[raw_sheet.source_file],
        sheet_name=raw_sheet.sheet_name,
        table_name=table_name,
        header_confidence=match.confidence,
        frame=frame,
        column_dtypes=column_dtypes,
    )


def _dedupe_table_names(tables: list[LoadedTable]) -> None:
    """Chống trùng table_name khi 2 nhóm schema khác nhau bị đặt cùng tên sau group_same_schema_files
    (thực tế xảy ra với dev_005: cùng tiền tố file nhưng schema lệch nhau giữa các tháng do
    split_quantity_unit tách khác nhau theo ngưỡng xác suất) -> tránh crash trùng tên trong DuckDB."""
    seen: dict[str, int] = {}
    for t in tables:
        name = t.table_name
        if name in seen:
            seen[name] += 1
            t.table_name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1


def build_business(business_dir: Path, out_dir: Path) -> dict:
    business_id = business_dir.name
    readme_path = business_dir / "README.md"
    readme: ReadmeInfo | None = parse_readme(readme_path) if readme_path.exists() else None

    tables: list[LoadedTable] = []
    for raw_sheet in read_all_sheets(business_dir):
        expected = (
            columns_for(readme, raw_sheet.source_file, raw_sheet.sheet_name) if readme else None
        )
        try:
            table = _clean_sheet_to_table(raw_sheet, expected)
            if table is not None:
                tables.append(table)
        except Exception:
            logger.warning(
                "Bỏ qua %s (sheet=%s) của %s do lỗi parse",
                raw_sheet.source_file,
                raw_sheet.sheet_name,
                business_id,
                exc_info=True,
            )

    tables = group_same_schema_files(tables)
    _dedupe_table_names(tables)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_tables(out_dir / f"{business_id}.duckdb", tables)

    readme_raw = readme.raw_text if readme else ""
    summary = summarize_business(business_id, tables, readme_raw)
    (out_dir / f"{business_id}.schema.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--biz-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    build_business(args.biz_dir, args.out)


if __name__ == "__main__":
    main()
