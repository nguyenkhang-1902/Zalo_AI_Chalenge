import csv
from pathlib import Path

import openpyxl

from data_loader.sheet_reader import read_all_sheets


def test_reads_csv_and_xlsx(tmp_path: Path):
    csv_path = tmp_path / "a.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Tên", "Giá"])
        w.writerow(["Cà phê", "20000"])

    xlsx_path = tmp_path / "b.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Mã", "Số lượng"])
    ws.append(["SP01", 5])
    wb.create_sheet("Sheet2")
    wb["Sheet2"].append(["X"])
    wb.save(xlsx_path)

    sheets = read_all_sheets(tmp_path)

    assert len(sheets) == 3  # 1 csv + 2 sheet trong xlsx
    csv_sheet = next(s for s in sheets if s.source_file == "a.csv")
    assert csv_sheet.sheet_name is None
    assert csv_sheet.rows == [("Tên", "Giá"), ("Cà phê", "20000")]

    xlsx_sheet1 = next(s for s in sheets if s.source_file == "b.xlsx" and s.sheet_name == "Sheet1")
    assert xlsx_sheet1.rows == [("Mã", "Số lượng"), ("SP01", 5)]
