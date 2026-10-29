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
