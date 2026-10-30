# tests/date_resolver/test_tet.py
from datetime import date
from pathlib import Path

from date_resolver.calendar_index import load_calendar
from date_resolver.tet import comparable_before_tet, tet_period

REAL_CALENDAR = Path(__file__).resolve().parents[2] / "train" / "calendar.csv"


def test_tet_period_2024_matches_real_calendar():
    index = load_calendar(str(REAL_CALENDAR))

    # 23 tháng Chạp âm 2023 = 2024-02-02; mùng 10 tháng Giêng âm 2024 = 2024-02-19
    assert tet_period(index, 2024) == (date(2024, 2, 2), date(2024, 2, 19))


def test_tet_period_returns_none_when_year_out_of_calendar_range():
    index = load_calendar(str(REAL_CALENDAR))

    assert tet_period(index, 1990) is None


def test_comparable_before_tet_2024_has_same_length_right_before_23_thang_chap():
    index = load_calendar(str(REAL_CALENDAR))

    # tet_period dài 18 ngày (2024-02-02 -> 2024-02-19) -> 18 ngày ngay trước 2024-02-02
    assert comparable_before_tet(index, 2024) == (date(2024, 1, 15), date(2024, 2, 1))


def test_comparable_before_tet_returns_none_when_tet_period_is_none():
    index = load_calendar(str(REAL_CALENDAR))

    assert comparable_before_tet(index, 1990) is None
