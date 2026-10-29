"""Đọc thô mọi sheet/csv trong 1 thư mục business, chưa xử lý header/kiểu dữ liệu."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import openpyxl


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
    sheets = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        sheets.append(RawSheet(source_file=path.name, sheet_name=sheet_name, rows=rows))
    wb.close()
    return sheets


def read_all_sheets(business_dir: Path) -> list[RawSheet]:
    """Đọc mọi file .csv/.xlsx trong business_dir, trả về danh sách RawSheet (chưa làm sạch)."""
    result: list[RawSheet] = []
    for path in sorted(business_dir.iterdir()):
        if path.suffix.lower() == ".csv":
            result.append(_read_csv(path))
        elif path.suffix.lower() == ".xlsx":
            result.extend(_read_xlsx(path))
    return result
