from data_loader.header_locator import locate_header


def test_finds_header_after_junk_rows_using_readme_columns():
    rows = [
        ("BẢNG KÊ PHIẾU GIAO HÀNG", None, None),
        ("Kỳ báo cáo: toàn bộ", None, None),
        (None, None, None),
        ("Ngày giao hàng", "Mã đơn hàng", "Số lượng giao"),
        ("02/02/2025", "ORD000002", 1),
    ]
    expected_columns = ["Ngày giao hàng", "Mã đơn hàng", "Số lượng giao"]

    match = locate_header(rows, expected_columns)

    assert match.header_row_index == 3
    assert match.confidence == "high"


def test_falls_back_to_heuristic_when_no_readme_columns():
    rows = [
        ("Tên", "Giá"),
        ("Cà phê", 20000),
    ]

    match = locate_header(rows, expected_columns=None)

    assert match.header_row_index == 0
    assert match.confidence == "low"
