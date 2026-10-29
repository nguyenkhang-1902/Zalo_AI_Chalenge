import csv
import sqlite3
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


def test_reads_each_sqlite_table_as_header_plus_rows(tmp_path: Path):
    con = sqlite3.connect(tmp_path / "pos.sqlite")
    con.execute("CREATE TABLE don_hang (MaDon TEXT PRIMARY KEY, TongTien INTEGER)")
    con.execute("CREATE TABLE san_pham (id INTEGER PRIMARY KEY AUTOINCREMENT, Ten TEXT)")
    con.executemany("INSERT INTO don_hang VALUES (?, ?)", [("D1", 100), ("D2", None)])
    con.execute("INSERT INTO san_pham (Ten) VALUES ('Paracetamol')")
    con.commit()
    con.close()

    sheets = read_all_sheets(tmp_path)

    # sqlite_sequence (bảng nội bộ do AUTOINCREMENT tạo) không được lọt vào
    assert [(s.source_file, s.sheet_name) for s in sheets] == [
        ("pos.sqlite", "don_hang"),
        ("pos.sqlite", "san_pham"),
    ]
    assert sheets[0].rows == [("MaDon", "TongTien"), ("D1", 100), ("D2", None)]
    assert sheets[1].rows == [("id", "Ten"), (1, "Paracetamol")]


def test_one_unreadable_file_does_not_stop_sibling_files(tmp_path: Path):
    (tmp_path / "good.csv").write_text("A\n1\n", encoding="utf-8")
    (tmp_path / "~$good.xlsx").write_bytes(b"lock file, not a zip")
    (tmp_path / "latin1.csv").write_bytes("Tên\nCà phê\n".encode("cp1258"))

    sheets = read_all_sheets(tmp_path)

    assert [s.source_file for s in sheets] == ["good.csv"]
