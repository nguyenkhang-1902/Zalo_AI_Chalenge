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


def test_skips_real_caption_rows_before_header_when_no_readme_columns():
    # Dữ liệu thật train/data/biz_118/Bảng kê phiếu giao hàng.xlsx: 2 dòng caption phía trên
    # header, mỗi dòng chỉ có 1 cell -- fallback (không có expected_columns) từng chọn nhầm dòng
    # caption đầu tiên làm header vì "mọi cell không rỗng đều là string" cũng đúng với dòng caption.
    rows = [
        ("BẢNG KÊ PHIẾU GIAO HÀNG",),
        ("Kỳ báo cáo: toàn bộ",),
        (),
        (
            "Ngày giao hàng", "Mã đơn hàng", "Lần giao", "Tên hàng hóa", "Đơn vị tính",
            "Số lượng giao", "Biển số xe", "Người giao hàng",
        ),
        ("02/02/2025", "ORD000002", 1, "Kẽm buộc 1mm", "kg", 1, "51C-327.66", "Ông Hương"),
    ]

    match = locate_header(rows, expected_columns=None)

    assert match.header_row_index == 3
    assert match.confidence == "low"


def test_falls_back_to_first_candidate_when_every_row_looks_like_a_caption():
    # Pathological case: nếu MỌI dòng string-only đều giống caption, phải vẫn trả về dòng ĐẦU
    # TIÊN trong số đó (không về index 0 cứng hoặc rơi hết), giữ an toàn như hành vi gốc.
    rows = [("TIÊU ĐỀ MỘT",), ("TIÊU ĐỀ HAI",)]

    match = locate_header(rows, expected_columns=None)

    assert match.header_row_index == 0
    assert match.confidence == "low"
