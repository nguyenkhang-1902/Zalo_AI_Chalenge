"""Orchestrator: README -> header locate -> clean -> group -> DuckDB + schema summary, 1 business."""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from data_loader.duckdb_writer import write_tables
from data_loader.header_locator import locate_header
from data_loader.models import LoadedTable
from data_loader.readme_parser import ReadmeInfo, columns_for, parse_readme
from data_loader.schema_grouping import _is_period_series, group_same_schema_files
from data_loader.schema_summary import summarize_business
from data_loader.sheet_reader import RawSheet, read_all_sheets
from data_loader.value_cleaner import (
    clean_numeric_column,
    parse_vn_date_column,
    parse_vn_money,
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


def _apply_value_cleaning(frame: pd.DataFrame) -> dict[str, str]:
    """Chạy cleaning numeric/date/số-lượng+đơn-vị trên 1 DataFrame đã có header, mutate frame tại
    chỗ, trả về column_dtypes. Dùng chung cho đường 1-file và đường gộp raw period-series, để quyết
    định tách số+đơn vị chỉ được đưa ra MỘT lần trên dữ liệu đã gộp (không lặp lại độc lập mỗi file,
    vốn có thể lật qua lại ngưỡng 0.5 khi noise thật khác nhau từng file)."""
    column_dtypes: dict[str, str] = {}
    for col in list(frame.columns):
        # Rule trong value_cleaner coi None là thiếu; .tolist() của pandas lại trả NaN/NaT
        # (isinstance(nan, float) -> True sẽ bị đếm như số hợp lệ) -> chuẩn hoá về None tại đây.
        values = [None if pd.isna(v) else v for v in frame[col].tolist()]

        # Tiền có hậu tố ("1.500đ") phải thử TRƯỚC split_quantity_unit, nếu không "đ" bị coi là
        # đơn vị và "1.500" thành 1.5 (lệch 1000 lần).
        cleaned, dtype = parse_vn_money(values)
        if dtype == "numeric":
            frame[col] = cleaned
            column_dtypes[col] = "numeric"
            continue

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
        if dtype in ("date", "datetime"):
            frame[col] = cleaned
            column_dtypes[col] = dtype
        else:
            column_dtypes[col] = "raw"
    return column_dtypes


def _clean_sheet_to_table(raw_sheet: RawSheet, expected_columns: list[str] | None) -> LoadedTable | None:
    match = locate_header(raw_sheet.rows, expected_columns)
    header_row = raw_sheet.rows[match.header_row_index]
    data_rows = raw_sheet.rows[match.header_row_index + 1 :]
    if not data_rows:
        return None

    header = _build_header(header_row)
    frame = pd.DataFrame(data_rows, columns=header)
    column_dtypes = _apply_value_cleaning(frame)

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


def _group_raw_period_series(
    raw_sheets: list[RawSheet], readme: ReadmeInfo | None
) -> tuple[list[list[RawSheet]], list[RawSheet]]:
    """Gom RawSheet (TRƯỚC khi clean) thành các nhóm period-series đáng tin cậy, để clean 1 lần
    trên dữ liệu gộp thay vì clean riêng từng file rồi mới gộp (xem _apply_value_cleaning).

    Chỉ gom các sheet cùng sheet_name VÀ có cùng danh sách cột khai báo ở README
    (`columns_for`) -- danh sách này ổn định cho mọi file khớp 1 template, không phụ thuộc
    nhiễu dữ liệu thật như khi gom theo cột đã clean. Sheet không có cột khai báo (không rõ
    README, hoặc README không có) luôn rơi về nhóm "singles" để xử lý từng file như cũ.
    Trong mỗi bucket, còn phải xác nhận tên file đúng là 1 chuỗi theo kỳ (dùng lại guard
    `_is_period_series` của schema_grouping) mới coi là 1 group; nếu không, trả về singles.
    """
    buckets: dict[tuple, list[RawSheet]] = defaultdict(list)
    singles: list[RawSheet] = []

    for rs in raw_sheets:
        expected = columns_for(readme, rs.source_file, rs.sheet_name) if readme else None
        if expected is None:
            singles.append(rs)
            continue
        buckets[(rs.sheet_name, tuple(expected))].append(rs)

    groups: list[list[RawSheet]] = []
    for bucket in buckets.values():
        if len(bucket) < 2:
            singles.extend(bucket)
            continue
        stems = [os.path.splitext(rs.source_file)[0] for rs in bucket]
        prefix = os.path.commonprefix(stems)
        if _is_period_series(stems, prefix):
            groups.append(bucket)
        else:
            singles.extend(bucket)

    return groups, singles


def _clean_raw_group_to_table(group: list[RawSheet], readme: ReadmeInfo | None) -> LoadedTable | None:
    """Gộp raw rows của 1 period-series group rồi clean MỘT LẦN trên dữ liệu đã gộp (FR-011)."""
    expected = columns_for(readme, group[0].source_file, group[0].sheet_name) if readme else None

    header: list[str] | None = None
    all_data_rows: list[tuple] = []
    confidences: list[str] = []
    for rs in group:
        match = locate_header(rs.rows, expected)
        confidences.append(match.confidence)
        member_header = _build_header(rs.rows[match.header_row_index])
        if header is None:
            header = member_header
        elif member_header != header:
            # Không nối positional 2 file header khác nhau -- pandas sẽ âm thầm pad NaN theo vị trí
            # cột thay vì raise, ra dữ liệu sai lặng lẽ (còn tệ hơn crash). Raise để try/except ở
            # build_business bắt, rơi các sheet trong group này về xử lý từng file riêng.
            raise ValueError(
                f"Header không khớp trong period-series group: {rs.source_file} có "
                f"{member_header!r}, khác header nhóm {group[0].source_file} là {header!r}"
            )
        all_data_rows.extend(rs.rows[match.header_row_index + 1 :])

    if not all_data_rows:
        return None

    frame = pd.DataFrame(all_data_rows, columns=header)
    column_dtypes = _apply_value_cleaning(frame)

    stems = [os.path.splitext(rs.source_file)[0] for rs in group]
    prefix = os.path.commonprefix(stems)
    table_name = re.sub(r"[_\-\d]+$", "", prefix) or "data"

    return LoadedTable(
        source_files=[rs.source_file for rs in group],
        sheet_name=group[0].sheet_name,
        table_name=table_name,
        header_confidence="low" if "low" in confidences else "high",
        frame=frame,
        column_dtypes=column_dtypes,
    )


def _dedupe_table_names(tables: list[LoadedTable]) -> None:
    """Chống trùng table_name khi 2 nhóm schema khác nhau bị đặt cùng tên sau group_same_schema_files
    (thực tế xảy ra với dev_005: cùng tiền tố file nhưng schema lệch nhau giữa các tháng do
    split_quantity_unit tách khác nhau theo ngưỡng xác suất) -> tránh crash trùng tên trong DuckDB.
    So sánh casefold vì identifier DuckDB không phân biệt hoa/thường kể cả khi quote ("DonHang" và
    "donhang" là 1 table); tên mới vẫn giữ nguyên casing gốc."""
    seen: set[str] = set()
    for t in tables:
        name, n = t.table_name, 1
        while name.casefold() in seen:
            n += 1
            name = f"{t.table_name}_{n}"
        t.table_name = name
        seen.add(name.casefold())


def build_business(business_dir: Path, out_dir: Path) -> dict:
    business_id = business_dir.name
    readme_path = business_dir / "README.md"
    readme: ReadmeInfo | None = parse_readme(readme_path) if readme_path.exists() else None

    raw_sheets = read_all_sheets(business_dir)
    groups, singles = _group_raw_period_series(raw_sheets, readme)

    tables: list[LoadedTable] = []

    for group in groups:
        try:
            table = _clean_raw_group_to_table(group, readme)
        except Exception:
            logger.warning(
                "Gộp raw period-series lỗi (%s) của %s, xử lý riêng từng file",
                [rs.source_file for rs in group],
                business_id,
                exc_info=True,
            )
            singles.extend(group)
            continue
        if table is not None:
            tables.append(table)

    for raw_sheet in singles:
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
    tables = write_tables(out_dir / f"{business_id}.duckdb", tables)

    readme_raw = readme.raw_text if readme else ""
    summary = summarize_business(business_id, tables, readme_raw)
    (out_dir / f"{business_id}.schema.json").write_text(
        # default=str: giá trị lạ lọt qua cột "raw" (vd datetime.time) không được làm sập cả business
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
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
