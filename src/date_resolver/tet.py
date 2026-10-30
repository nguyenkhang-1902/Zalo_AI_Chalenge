"""Khoảng ngày Tết — tra trực tiếp từ CalendarIndex, không tự tính âm lịch."""
from __future__ import annotations

from datetime import date, timedelta

from .calendar_index import CalendarIndex


def tet_period(calendar_index: CalendarIndex, year: int) -> tuple[date, date] | None:
    start = calendar_index.lunar_to_solar.get((23, 12, year - 1))
    end = calendar_index.lunar_to_solar.get((10, 1, year))
    if start is None or end is None:
        return None
    return (start, end)


def comparable_before_tet(calendar_index: CalendarIndex, year: int) -> tuple[date, date] | None:
    period = tet_period(calendar_index, year)
    if period is None:
        return None

    start, end = period
    length = (end - start).days + 1
    before_end = start - timedelta(days=1)
    before_start = before_end - timedelta(days=length - 1)
    return (before_start, before_end)
