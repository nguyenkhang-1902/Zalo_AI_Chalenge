# tests/date_resolver/test_date_resolver_month.py
from datetime import date

import pytest

from date_resolver.date_resolver import (
    comparable_last_month,
    month_of,
    month_or_quarter_without_year,
    shift_session,
    this_month,
)


def test_month_of_returns_full_calendar_month():
    assert month_of(2, 2024) == (date(2024, 2, 1), date(2024, 2, 29))  # 2024 nhuận


def test_month_of_rejects_invalid_month():
    with pytest.raises(ValueError):
        month_of(13, 2024)


def test_month_of_rejects_non_int_month():
    with pytest.raises(ValueError):
        month_of("2", 2024)


def test_month_of_rejects_bool_month():
    with pytest.raises(ValueError):
        month_of(True, 2024)


def test_this_month_from_day_1_to_today():
    assert this_month(date(2026, 10, 30)) == (date(2026, 10, 1), date(2026, 10, 30))


def test_comparable_last_month_same_day_number():
    assert comparable_last_month(date(2026, 10, 30)) == (date(2026, 9, 1), date(2026, 9, 30))


def test_comparable_last_month_clamps_when_previous_month_shorter():
    # tháng 3/2026 có 31 ngày, tháng 2/2026 chỉ có 28 -> lấy hết tháng 2
    assert comparable_last_month(date(2026, 3, 31)) == (date(2026, 2, 1), date(2026, 2, 28))


def test_comparable_last_month_wraps_year_at_january():
    assert comparable_last_month(date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 15))


def test_month_without_year_uses_this_year_when_not_future():
    # hôm nay 2026-10-30, hỏi "tháng 10" (đang diễn ra) -> năm nay
    assert month_or_quarter_without_year(date(2026, 10, 30), month=10) == (
        date(2026, 10, 1),
        date(2026, 10, 31),
    )


def test_month_without_year_uses_last_year_when_future():
    # hôm nay 2026-10-30, hỏi "tháng 11" (chưa tới) -> năm trước
    assert month_or_quarter_without_year(date(2026, 10, 30), month=11) == (
        date(2025, 11, 1),
        date(2025, 11, 30),
    )


def test_quarter_without_year_uses_this_year_when_not_future():
    # Q4 bắt đầu 01/10, hôm nay 30/10 -> đã bắt đầu -> năm nay
    assert month_or_quarter_without_year(date(2026, 10, 30), quarter=4) == (
        date(2026, 10, 1),
        date(2026, 12, 31),
    )


def test_month_without_year_inclusive_when_as_of_is_first_day_of_month():
    # hôm nay đúng ngày 1 của tháng 3 -> "chưa sau hôm nay" (đúng = hôm nay) -> năm nay
    assert month_or_quarter_without_year(date(2026, 3, 1), month=3) == (
        date(2026, 3, 1),
        date(2026, 3, 31),
    )


def test_quarter_without_year_inclusive_when_as_of_is_first_day_of_quarter():
    # hôm nay đúng ngày 1 của Q2 (01/04) -> năm nay
    assert month_or_quarter_without_year(date(2026, 4, 1), quarter=2) == (
        date(2026, 4, 1),
        date(2026, 6, 30),
    )


def test_quarter_without_year_rejects_out_of_range_quarter():
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30), quarter=5)
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30), quarter=0)


def test_month_or_quarter_requires_exactly_one_arg():
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30))
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30), month=5, quarter=2)


def test_month_or_quarter_rejects_non_int_month():
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30), month="10")


def test_month_or_quarter_rejects_bool_month():
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30), month=True)


def test_month_or_quarter_rejects_non_int_quarter():
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30), quarter="4")


def test_month_or_quarter_rejects_bool_quarter():
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30), quarter=True)


def test_shift_session_morning_afternoon_and_outside():
    assert shift_session(10) == "sáng"
    assert shift_session(15) == "chiều"
    assert shift_session(23) is None


def test_shift_session_rejects_invalid_hour():
    with pytest.raises(ValueError):
        shift_session(24)


def test_shift_session_rejects_non_int_hour():
    with pytest.raises(ValueError):
        shift_session("10")


def test_shift_session_rejects_bool_hour():
    with pytest.raises(ValueError):
        shift_session(True)
