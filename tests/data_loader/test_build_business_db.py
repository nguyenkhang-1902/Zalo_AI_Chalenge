import json
from datetime import datetime, time
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from data_loader.build_business_db import (
    _apply_value_cleaning,
    _build_header,
    _dedupe_table_names,
    build_business,
)
from data_loader.models import LoadedTable


def test_value_cleaning_treats_pandas_nan_and_nat_as_missing():
    """Input thật là DataFrame (.tolist() ra NaN/NaT, không phải None) -- cột "Ghi chú" gần như
    trống không được bị coi là numeric rồi xoá mất chữ, cột ngày thiếu không được ra chuỗi 'NaT'."""
    frame = pd.DataFrame(
        {
            "Ghi chú": [None, np.nan, "Giao gấp", np.nan, None, np.nan, np.nan, np.nan, np.nan, np.nan],
            "Ngày": [datetime(2025, 1, 2), None] + [datetime(2025, 1, 3)] * 8,
        }
    )

    dtypes = _apply_value_cleaning(frame)

    assert dtypes["Ghi chú"] != "numeric"
    assert "Giao gấp" in frame["Ghi chú"].tolist()
    assert dtypes["Ngày"] == "date"
    assert "NaT" not in frame["Ngày"].tolist()
    assert pd.isna(frame["Ngày"].tolist()[1])


def test_value_cleaning_parses_money_before_quantity_unit():
    frame = pd.DataFrame({"Giá 1 đv": ["1.500đ", "79k", 2760000, "2,76tr"]})

    dtypes = _apply_value_cleaning(frame)

    assert dtypes == {"Giá 1 đv": "numeric"}
    assert frame["Giá 1 đv"].tolist() == [1500.0, 79000.0, 2760000.0, 2760000.0]


def _table(name: str) -> LoadedTable:
    return LoadedTable([f"{name}.csv"], None, name, "high", pd.DataFrame({"a": [1]}))


def test_dedupe_table_names_is_case_insensitive_and_keeps_casing():
    tables = [_table("DonHang"), _table("donhang"), _table("DONHANG"), _table("donhang_2")]

    _dedupe_table_names(tables)

    assert [t.table_name for t in tables] == ["DonHang", "donhang_2", "DONHANG_3", "donhang_2_2"]


def test_build_business_writes_schema_json_with_time_of_day_raw_column(tmp_path: Path):
    """Cột "Giờ" kiểu time trong xlsx (như dev_004) ở lại "raw" -> sample_values chứa
    datetime.time, json.dumps không có default=str sẽ TypeError làm sập cả business."""
    business_dir = tmp_path / "biz"
    business_dir.mkdir()
    wb = openpyxl.Workbook()
    wb.active.append(["Mã", "Giờ"])
    wb.active.append(["A1", time(8, 30)])
    wb.save(business_dir / "a.xlsx")

    build_business(business_dir, tmp_path / "out")

    written = json.loads((tmp_path / "out" / "biz.schema.json").read_text(encoding="utf-8"))
    gio = next(c for c in written["tables"][0]["columns"] if c["name"] == "Giờ")
    assert gio["sample_values"] == ["08:30:00"]


def test_build_header_dedupes_case_insensitively():
    # DuckDB không phân biệt hoa/thường tên cột (giống _dedupe_table_names đã làm cho table) --
    # "Ten" và "ten" phải bị coi là trùng.
    header = _build_header(("Ten", "ten", "Ghi chú", "Ghi chú"))

    assert header == ["Ten", "ten_2", "Ghi chú", "Ghi chú_2"]


def test_build_header_avoids_colliding_with_an_existing_original_name():
    # Tên sinh ra để dedupe ("Ten_2") không được đụng 1 tên gốc đã có sẵn trong header.
    header = _build_header(("Ten", "Ten", "Ten_2"))

    assert header == ["Ten", "Ten_2", "Ten_2_2"]
    assert len({h.casefold() for h in header}) == 3
