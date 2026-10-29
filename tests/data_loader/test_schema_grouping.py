import pandas as pd

from data_loader.models import LoadedTable
from data_loader.schema_grouping import group_same_schema_files


def _table(source_file: str, data: dict) -> LoadedTable:
    return LoadedTable(
        source_files=[source_file],
        sheet_name=None,
        table_name=source_file.rsplit(".", 1)[0],
        header_confidence="high",
        frame=pd.DataFrame(data),
    )


def test_groups_monthly_files_with_same_schema_and_numeric_suffix():
    jan = _table("BanHang_Thang01_2025.xlsx", {"Mã đơn": ["A1"], "Tổng tiền": [1000]})
    feb = _table("BanHang_Thang02_2025.xlsx", {"Mã đơn": ["B1"], "Tổng tiền": [2000]})
    jan.column_dtypes = {"Tổng tiền": "numeric"}
    feb.column_dtypes = {"Tổng tiền": "numeric"}
    danh_muc = _table("DanhMuc.xlsx", {"Mã hàng": ["SP1"], "Tên": ["Cà phê"]})

    result = group_same_schema_files([jan, feb, danh_muc])

    assert len(result) == 2
    merged = next(t for t in result if len(t.source_files) == 2)
    assert set(merged.source_files) == {"BanHang_Thang01_2025.xlsx", "BanHang_Thang02_2025.xlsx"}
    assert len(merged.frame) == 2
    assert merged.column_dtypes == {"Tổng tiền": "numeric"}
    assert merged.table_name.startswith("BanHang")
    standalone = next(t for t in result if len(t.source_files) == 1)
    assert standalone.table_name == "DanhMuc"


def test_does_not_group_same_schema_with_unrelated_text_suffix():
    a = _table("DanhSachKhachA.csv", {"Tên": ["X"], "SDT": ["0900"]})
    b = _table("DanhSachNhaCungCap.csv", {"Tên": ["Y"], "SDT": ["0911"]})

    result = group_same_schema_files([a, b])

    assert len(result) == 2  # đuôi tên không phải số -> không gộp nhầm
