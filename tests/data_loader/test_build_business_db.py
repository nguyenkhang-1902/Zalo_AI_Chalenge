import json
import warnings
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


def test_clean_sheet_to_table_pads_short_rows_without_pandas_warning(tmp_path: Path):
    """Finding #8: dòng ngắn hơn header (xlsx có dòng bị cắt cell rỗng ở cuối) không được để pandas
    tự pad NaN lúc dựng DataFrame -- Pandas4Warning, dự kiến raise lỗi ở bản sau."""
    business_dir = tmp_path / "biz"
    business_dir.mkdir()
    (business_dir / "a.csv").write_text("A,B,C\n1,2\n3,4,5\n", encoding="utf-8")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        summary = build_business(business_dir, tmp_path / "out")

    table = next(t for t in summary["tables"] if t["table_name"] == "a")
    col_c = table["columns"][2]
    assert col_c["n_rows"] == 2  # cả 2 dòng đều có mặt, dòng ngắn được pad None ở "C"
    assert col_c["n_null"] == 1  # giá trị pad thực sự là None/NaN, không phải sentinel khác
    assert col_c["sample_values"] == [5.0]  # chỉ dòng dài (3,4,5) có giá trị "C", dòng ngắn là null


def test_clean_sheet_to_table_truncates_long_rows_without_pandas_warning(tmp_path: Path):
    """Finding #8: dòng dài hơn header (thừa cell) phải bị cắt về đúng độ dài header TRƯỚC khi
    dựng DataFrame -- không để pandas tự xử lý/raise, không lệch cột."""
    business_dir = tmp_path / "biz"
    business_dir.mkdir()
    (business_dir / "a.csv").write_text("A,B\n1,2,3\n4,5\n", encoding="utf-8")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        summary = build_business(business_dir, tmp_path / "out")

    table = next(t for t in summary["tables"] if t["table_name"] == "a")
    assert table["columns"][0]["n_rows"] == 2
    col_a = next(c for c in table["columns"] if c["name"] == "A")
    assert col_a["sample_values"] == [1, 4]  # dòng "1,2,3" bị cắt về đúng 2 cột, giữ "A"=1, "B"=2, bỏ "3"
