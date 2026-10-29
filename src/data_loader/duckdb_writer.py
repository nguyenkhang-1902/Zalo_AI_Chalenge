"""Ghi các LoadedTable đã làm sạch vào 1 file DuckDB (ghi đè sạch mỗi lần chạy)."""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from data_loader.models import LoadedTable

logger = logging.getLogger(__name__)


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def write_tables(db_path: Path, tables: list[LoadedTable]) -> list[LoadedTable]:
    """Trả về các table ghi thành công, để schema summary không liệt kê table không có trong DB."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    written: list[LoadedTable] = []
    con = duckdb.connect(str(db_path))
    try:
        for table in tables:
            # 1 table lỗi (vd trùng tên) chỉ bỏ qua table đó, không huỷ cả lần ghi (Điều 7).
            try:
                con.register("tmp_df", table.frame)
                con.execute(f"CREATE TABLE {_quote_ident(table.table_name)} AS SELECT * FROM tmp_df")
                written.append(table)
            except Exception:
                logger.warning("Bỏ qua table không ghi được: %s", table.table_name, exc_info=True)
            finally:
                con.unregister("tmp_df")
    finally:
        con.close()
    return written
