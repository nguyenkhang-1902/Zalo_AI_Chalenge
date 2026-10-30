from datetime import date
from pathlib import Path

import pytest

from date_resolver.calendar_index import load_calendar

REAL_CALENDAR = Path(__file__).resolve().parents[2] / "train" / "calendar.csv"


def test_looks_up_real_lunar_date_for_mung_1_tet_2024():
    index = load_calendar(str(REAL_CALENDAR))

    assert index.lunar_to_solar[(1, 1, 2024)] == date(2024, 2, 10)


def test_looks_up_real_lunar_date_for_23_thang_chap_2023():
    index = load_calendar(str(REAL_CALENDAR))

    assert index.lunar_to_solar[(23, 12, 2023)] == date(2024, 2, 2)


def test_non_leap_month_is_not_overwritten_by_leap_month_with_same_number():
    index = load_calendar(str(REAL_CALENDAR))

    assert index.lunar_to_solar[(1, 6, 2025)] == date(2025, 6, 25)


def test_missing_required_column_raises_value_error(tmp_path):
    bad_csv = tmp_path / "calendar.csv"
    bad_csv.write_text("date,weekday,holiday\n2024-01-01,1,Tết Dương lịch\n", encoding="utf-8")

    with pytest.raises(ValueError, match="thiếu cột"):
        load_calendar(str(bad_csv))


def test_missing_lunar_leap_column_raises_value_error(tmp_path):
    bad_csv = tmp_path / "calendar.csv"
    bad_csv.write_text(
        "date,lunar_day,lunar_month,lunar_year\n2024-02-10,1,1,2024\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="thiếu cột"):
        load_calendar(str(bad_csv))
