"""Toán khoảng ngày thuần dương lịch — không phụ thuộc lịch âm."""
from __future__ import annotations

import calendar as _cal_mod
from datetime import date, timedelta


def today(as_of: date) -> tuple[date, date]:
    return (as_of, as_of)


def n_days_ago(as_of: date, n: int) -> tuple[date, date]:
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError(f"n phải là int, got {type(n).__name__}")
    if n < 1:
        raise ValueError(f"n phải >= 1, got {n}")
    return (as_of - timedelta(days=n - 1), as_of)


def this_week(as_of: date) -> tuple[date, date]:
    monday = as_of - timedelta(days=as_of.weekday())
    return (monday, as_of)


def last_week(as_of: date) -> tuple[date, date]:
    this_monday = as_of - timedelta(days=as_of.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    return (last_monday, last_sunday)


def year_to_date(as_of: date) -> tuple[date, date]:
    return (date(as_of.year, 1, 1), as_of)


def month_of(month: int, year: int) -> tuple[date, date]:
    if not isinstance(month, int) or isinstance(month, bool):
        raise ValueError(f"month phải là int, got {type(month).__name__}")
    if not 1 <= month <= 12:
        raise ValueError(f"month phải 1-12, got {month}")
    last_day = _cal_mod.monthrange(year, month)[1]
    return (date(year, month, 1), date(year, month, last_day))


def this_month(as_of: date) -> tuple[date, date]:
    return (date(as_of.year, as_of.month, 1), as_of)


def comparable_last_month(as_of: date) -> tuple[date, date]:
    if as_of.month == 1:
        prev_year, prev_month = as_of.year - 1, 12
    else:
        prev_year, prev_month = as_of.year, as_of.month - 1

    last_day_prev = _cal_mod.monthrange(prev_year, prev_month)[1]
    end_day = min(as_of.day, last_day_prev)
    return (date(prev_year, prev_month, 1), date(prev_year, prev_month, end_day))


def month_or_quarter_without_year(
    as_of: date, month: int | None = None, quarter: int | None = None
) -> tuple[date, date]:
    if (month is None) == (quarter is None):
        raise ValueError("phải truyền đúng 1 trong 2: month hoặc quarter")

    if month is not None:
        if not isinstance(month, int) or isinstance(month, bool):
            raise ValueError(f"month phải là int, got {type(month).__name__}")
        if not 1 <= month <= 12:
            raise ValueError(f"month phải 1-12, got {month}")
        start_month, end_month = month, month
    else:
        if not isinstance(quarter, int) or isinstance(quarter, bool):
            raise ValueError(f"quarter phải là int, got {type(quarter).__name__}")
        if not 1 <= quarter <= 4:
            raise ValueError(f"quarter phải 1-4, got {quarter}")
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2

    candidate_start = date(as_of.year, start_month, 1)
    year = as_of.year if candidate_start <= as_of else as_of.year - 1
    end_day = _cal_mod.monthrange(year, end_month)[1]
    return (date(year, start_month, 1), date(year, end_month, end_day))


def shift_session(hour: int) -> str | None:
    if not isinstance(hour, int) or isinstance(hour, bool):
        raise ValueError(f"hour phải là int, got {type(hour).__name__}")
    if not 0 <= hour <= 23:
        raise ValueError(f"hour phải 0-23, got {hour}")
    if 6 <= hour <= 13:
        return "sáng"
    if 14 <= hour <= 21:
        return "chiều"
    return None
