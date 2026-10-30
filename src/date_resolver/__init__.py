"""Bộ hàm tính khoảng ngày theo rulebook.md §2 — xem specs/002-date-calendar-resolver/spec.md."""
from .calendar_index import CalendarIndex, load_calendar
from .date_resolver import (
    comparable_last_month,
    last_week,
    month_of,
    month_or_quarter_without_year,
    n_days_ago,
    shift_session,
    this_month,
    this_week,
    today,
    year_to_date,
)
from .tet import comparable_before_tet, tet_period

__all__ = [
    "CalendarIndex",
    "load_calendar",
    "today",
    "n_days_ago",
    "this_week",
    "last_week",
    "year_to_date",
    "month_of",
    "this_month",
    "comparable_last_month",
    "month_or_quarter_without_year",
    "shift_session",
    "tet_period",
    "comparable_before_tet",
]
