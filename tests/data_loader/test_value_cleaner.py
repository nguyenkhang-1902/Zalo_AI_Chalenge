from datetime import date, datetime

from data_loader.value_cleaner import (
    clean_numeric_column,
    parse_vn_date_column,
    parse_vn_money,
    split_quantity_unit,
)


def test_parse_vn_money_dot_thousand_with_currency_suffix():
    values = ["1.500đ", "2.148.900đ", "380.000 VND", "50000 đồng", None]

    cleaned, dtype = parse_vn_money(values)

    assert dtype == "numeric"
    assert cleaned == [1500.0, 2148900.0, 380000.0, 50000.0, None]


def test_parse_vn_money_k_and_tr_suffixes_mixed_with_plain_numbers():
    # Dạng thật từ dev_004/dev_007: "2,76tr" (phẩy thập phân), "5tr520" (= 5.520.000, đã đối
    # chiếu SL x đơn giá trên dữ liệu thật), số thường int/str trộn lẫn.
    values = ["79k", "69", 2760000, "5tr", "2,76tr", "1,14tr", "5tr520", "3 triệu"]

    cleaned, dtype = parse_vn_money(values)

    assert dtype == "numeric"
    assert cleaned == [79000.0, 69.0, 2760000.0, 5000000.0, 2760000.0, 1140000.0, 5520000.0, 3000000.0]


def test_parse_vn_money_keeps_negative_sign_of_return_rows():
    assert parse_vn_money(["-55.000đ", "-1,2tr", "120k", -55000]) == (
        [-55000.0, -1200000.0, 120000.0, -55000.0],
        "numeric",
    )


def test_parse_vn_money_does_not_fire_on_quantity_unit_column():
    values = ["1 kg", "2 cái", 5, None]

    assert parse_vn_money(values)[1] == "raw"
    assert split_quantity_unit(values) == ([1.0, 2.0, 5.0, None], ["kg", "cái", None, None])


def test_parse_vn_money_does_not_fire_on_plain_numbers_or_guess_ambiguous_shorthand():
    assert parse_vn_money([1, "2", 3.5])[1] == "raw"  # không có hậu tố -> để clean_numeric_column lo
    # "1tr2" mơ hồ (1.200.000 hay 1.002.000?) -> không đoán, cột rơi về raw
    assert parse_vn_money(["1tr2", "3tr4"]) == (["1tr2", "3tr4"], "raw")


def test_clean_numeric_column_handles_thousand_separator_mixed_with_plain_number():
    values = [42000, "51,000", "45000", None]

    cleaned, dtype = clean_numeric_column(values)

    assert dtype == "numeric"
    assert cleaned == [42000.0, 51000.0, 45000.0, None]


def test_clean_numeric_column_falls_back_to_raw_when_mostly_non_numeric():
    values = ["Đã hoàn thành", "Đã huỷ", "Đang giao"]

    cleaned, dtype = clean_numeric_column(values)

    assert dtype == "raw"
    assert cleaned == values


def test_split_quantity_unit_extracts_number_and_unit_when_majority_match():
    values = ["1 kg", "2 cái", 5, None]

    result = split_quantity_unit(values)

    assert result is not None
    numbers, units = result
    assert numbers == [1.0, 2.0, 5.0, None]
    assert units == ["kg", "cái", None, None]


def test_split_quantity_unit_returns_none_when_pattern_is_rare():
    values = [1, 2, 3, "1 kg"]

    assert split_quantity_unit(values) is None


def test_parse_vn_date_column_returns_real_date_objects_not_iso_strings():
    values = ["01/04/2025", "31/05/2025", None]

    cleaned, dtype = parse_vn_date_column(values)

    assert dtype == "date"
    assert cleaned == [date(2025, 4, 1), date(2025, 5, 31), None]


def test_parse_vn_date_column_keeps_real_time_of_day_from_datetime_objects():
    # Dữ liệu thật train/data/biz_105/SoBanHang_1.xlsx, sheet "Thang 02 2025": openpyxl tự parse
    # cell Excel có giờ thành datetime.datetime object thật (không phải text) -- bug gốc là
    # _parse_one gọi .date() bỏ mất giờ của CHÍNH object này, không phải thiếu format text.
    values = [
        datetime(2025, 2, 1, 6, 0, 25),
        datetime(2025, 2, 1, 6, 46, 58),
        None,
    ]

    cleaned, dtype = parse_vn_date_column(values)

    assert dtype == "datetime"
    assert cleaned == [datetime(2025, 2, 1, 6, 0, 25), datetime(2025, 2, 1, 6, 46, 58), None]


def test_parse_vn_date_column_upgrades_whole_column_to_datetime_when_any_value_has_time():
    # 1 giá trị có giờ thật đủ để NÂNG CẢ CỘT thành "datetime" -- các giá trị chỉ có ngày (00:00:00)
    # trong CÙNG cột phải lên datetime lúc nửa đêm để cột đồng nhất 1 kiểu (DuckDB infer TIMESTAMP
    # cho cả cột, không lẫn DATE/TIMESTAMP giữa các dòng).
    values = [datetime(2025, 2, 1, 0, 0, 0), datetime(2025, 2, 1, 6, 0, 25)]

    cleaned, dtype = parse_vn_date_column(values)

    assert dtype == "datetime"
    assert cleaned == [datetime(2025, 2, 1, 0, 0, 0), datetime(2025, 2, 1, 6, 0, 25)]
