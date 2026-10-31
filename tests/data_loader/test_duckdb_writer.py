from datetime import date, datetime
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


def test_date_and_datetime_columns_get_native_duckdb_types_not_varchar(tmp_path: Path):
    """Finding #2: parse_vn_date_column trả object date/datetime thật (không phải isoformat string)
    -- DuckDB phải suy ra DATE/TIMESTAMP thật để EXTRACT()/date function dùng được, không VARCHAR."""
    db_path = tmp_path / "biz.duckdb"
    table = LoadedTable(
        source_files=["a.csv"],
        sheet_name=None,
        table_name="DonHang",
        header_confidence="high",
        frame=pd.DataFrame(
            {
                "Ngày": [date(2025, 1, 2), None, date(2025, 1, 3)],
                "Giờ vào": [datetime(2025, 1, 2, 6, 30, 0), None, datetime(2025, 1, 3, 0, 0, 0)],
            }
        ),
    )

    write_tables(db_path, [table])

    con = duckdb.connect(str(db_path))
    types = dict(
        con.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'DonHang'"
        ).fetchall()
    )
    con.close()
    assert types["Ngày"] == "DATE"
    assert types["Giờ vào"] == "TIMESTAMP"
