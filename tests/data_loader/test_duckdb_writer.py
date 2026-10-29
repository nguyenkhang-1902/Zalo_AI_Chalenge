from pathlib import Path

import duckdb
import pandas as pd

from data_loader.duckdb_writer import write_tables
from data_loader.models import LoadedTable


def test_writes_and_overwrites_tables_idempotently(tmp_path: Path):
    db_path = tmp_path / "biz.duckdb"
    table = LoadedTable(
        source_files=["a.csv"],
        sheet_name=None,
        table_name="Khách hàng",
        header_confidence="high",
        frame=pd.DataFrame({"Tên": ["An", "Bình"]}),
    )

    write_tables(db_path, [table])
    write_tables(db_path, [table])  # chạy lại -> không được nhân đôi dòng

    con = duckdb.connect(str(db_path))
    rows = con.execute('SELECT "Tên" FROM "Khách hàng" ORDER BY "Tên"').fetchall()
    con.close()

    assert rows == [("An",), ("Bình",)]


def test_one_failing_table_does_not_abort_the_others(tmp_path: Path):
    db_path = tmp_path / "biz.duckdb"
    first = LoadedTable(["a.csv"], None, "DonHang", "high", pd.DataFrame({"x": [1]}))
    clash = LoadedTable(["b.csv"], None, "donhang", "high", pd.DataFrame({"x": [2]}))  # trùng (không phân biệt hoa/thường)
    last = LoadedTable(["c.csv"], None, "KhachHang", "high", pd.DataFrame({"y": [3]}))

    written = write_tables(db_path, [first, clash, last])

    assert [t.table_name for t in written] == ["DonHang", "KhachHang"]
    con = duckdb.connect(str(db_path))
    assert con.execute('SELECT y FROM "KhachHang"').fetchall() == [(3,)]
    con.close()
