"""Đọc thô mọi sheet/csv trong 1 thư mục business, chưa xử lý header/kiểu dữ liệu."""
from __future__ import annotations

import csv
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import openpyxl

logger = logging.getLogger(__name__)


@dataclass
class RawSheet:
    source_file: str
    sheet_name: str | None
    rows: list[tuple]


def _read_csv(path: Path) -> RawSheet:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = [tuple(row) for row in csv.reader(f)]
    return RawSheet(source_file=path.name, sheet_name=None, rows=rows)


def _read_xlsx(path: Path) -> list[RawSheet]:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        return [
            RawSheet(
                source_file=path.name,
                sheet_name=sheet_name,
                rows=list(wb[sheet_name].iter_rows(values_only=True)),
            )
            for sheet_name in wb.sheetnames
        ]
    finally:
        wb.close()


def _read_sqlite(path: Path) -> list[RawSheet]:
    """Mỗi table sqlite -> 1 RawSheet dạng [dòng header] + dòng dữ liệu, giống csv/xlsx."""
    con = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        table_names = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        sheets = []
        for name in table_names:
            cursor = con.execute(f'SELECT * FROM "{name.replace(chr(34), chr(34) * 2)}"')
            header = tuple(d[0] for d in cursor.description)
            sheets.append(
                RawSheet(source_file=path.name, sheet_name=name, rows=[header, *cursor.fetchall()])
            )
        return sheets
    finally:
        con.close()


_READERS = {
    ".csv": lambda p: [_read_csv(p)],
    ".xlsx": _read_xlsx,
    ".sqlite": _read_sqlite,
    ".db": _read_sqlite,
}


def read_all_sheets(business_dir: Path) -> list[RawSheet]:
    """Đọc mọi file .csv/.xlsx/.sqlite/.db trong business_dir, trả về danh sách RawSheet (chưa làm
    sạch). 1 file hỏng (xlsx lỗi, file khoá ~$x.xlsx, csv không phải UTF-8...) chỉ bị bỏ qua, các
    file khác vẫn được đọc (Điều 7 / FR-008)."""
    result: list[RawSheet] = []
    for path in sorted(business_dir.iterdir()):
        reader = _READERS.get(path.suffix.lower())
        if reader is None:
            continue
        try:
            result.extend(reader(path))
        except Exception:
            logger.warning("Bỏ qua file không đọc được: %s", path, exc_info=True)
    return result
