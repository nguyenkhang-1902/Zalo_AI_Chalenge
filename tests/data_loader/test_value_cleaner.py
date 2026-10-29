from data_loader.value_cleaner import (
    clean_numeric_column,
    parse_vn_date_column,
    split_quantity_unit,
)


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


def test_parse_vn_date_column_converts_to_iso():
    values = ["01/04/2025", "31/05/2025", None]

    cleaned, dtype = parse_vn_date_column(values)

    assert dtype == "date"
    assert cleaned == ["2025-04-01", "2025-05-31", None]
