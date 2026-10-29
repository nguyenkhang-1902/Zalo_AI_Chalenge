"""Ghi các LoadedTable đã làm sạch vào 1 file DuckDB (ghi đè sạch mỗi lần chạy)."""
from __future__ import annotations

from pathlib import Path

import duckdb

from data_loader.models import LoadedTable


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def write_tables(db_path: Path, tables: list[LoadedTable]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        for table in tables:
            con.register("tmp_df", table.frame)
            con.execute(f"CREATE TABLE {_quote_ident(table.table_name)} AS SELECT * FROM tmp_df")
            con.unregister("tmp_df")
    finally:
        con.close()
