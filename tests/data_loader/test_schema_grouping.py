import pandas as pd

from data_loader.models import LoadedTable
from data_loader.schema_grouping import _is_period_sheet_name, group_same_schema_files


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


def test_is_period_sheet_name_matches_all_real_patterns_found_in_the_dataset():
    # Toàn bộ pattern thật đã quét được từ train/ + public_test/ (xem Task 6 bối cảnh).
    real_period_names = [
        "T01_2025", "T06_2026",       # biz_102, biz_112
        "04.2025", "07.2026",          # biz_103, biz_115, biz_120, biz_128
        "Thang 02 2025", "Thang 01 2026",  # biz_105
        "Tháng 01-2025", "Tháng 05-2026",  # biz_117
        "T02-2025", "T09-2026",        # biz_118, biz_119, biz_122, dev_004
        "T7-2025", "T8-2026",          # dev_012, dev_014 (không đệm số 0)
    ]
    for name in real_period_names:
        assert _is_period_sheet_name(name), f"{name!r} phải khớp pattern kỳ"

    not_period_names = ["Ghi tắt", "DanhMuc", "KhachHang", "NhapHang", "KhuyenMai", None]
    for name in not_period_names:
        assert not _is_period_sheet_name(name), f"{name!r} KHÔNG được khớp pattern kỳ"


def test_groups_sheets_sharing_a_single_file_by_period_sheet_name():
    # Mô phỏng biz_102: 1 file, nhiều sheet tên theo kỳ, cùng schema (cùng cột sau khi clean).
    jan = _table("DonHang_ChiTiet.xlsx", {"Mã đơn hàng": ["A1"], "Tổng tiền": [1000]})
    jan.sheet_name = "T01_2025"
    feb = _table("DonHang_ChiTiet.xlsx", {"Mã đơn hàng": ["B1"], "Tổng tiền": [2000]})
    feb.sheet_name = "T02_2025"

    result = group_same_schema_files([jan, feb])

    assert len(result) == 1
    merged = result[0]
    assert len(merged.frame) == 2
    assert merged.source_files == ["DonHang_ChiTiet.xlsx", "DonHang_ChiTiet.xlsx"]


def test_does_not_pull_a_non_period_sheet_into_the_period_group():
    # Mô phỏng dev_014: sheet "Ghi tắt" tình cờ CÙNG schema với các sheet kỳ, nhưng tên sheet
    # không khớp pattern kỳ -- không được bị kéo vào nhóm gộp.
    t7 = _table("SoBanHang.xlsx", {"Mã": ["X1"], "Tiền": [500]})
    t7.sheet_name = "T7-2025"
    t8 = _table("SoBanHang.xlsx", {"Mã": ["X2"], "Tiền": [600]})
    t8.sheet_name = "T8-2025"
    ghi_tat = _table("SoBanHang.xlsx", {"Mã": ["X3"], "Tiền": [700]})
    ghi_tat.sheet_name = "Ghi tắt"

    result = group_same_schema_files([t7, t8, ghi_tat])

    assert len(result) == 2
    merged = next(t for t in result if len(t.source_files) > 1)
    assert len(merged.frame) == 2
    standalone = next(t for t in result if len(t.source_files) == 1)
    assert standalone.sheet_name == "Ghi tắt"
    assert len(standalone.frame) == 1


def test_file_based_period_grouping_still_takes_priority_when_it_matches():
    # Hành vi gốc (gộp theo hậu tố tên FILE, sheet_name=None) phải giữ nguyên không đổi.
    jan = _table("BanHang_Thang01_2025.xlsx", {"Mã đơn": ["A1"], "Tổng tiền": [1000]})
    feb = _table("BanHang_Thang02_2025.xlsx", {"Mã đơn": ["B1"], "Tổng tiền": [2000]})

    result = group_same_schema_files([jan, feb])

    assert len(result) == 1
    assert len(result[0].frame) == 2
