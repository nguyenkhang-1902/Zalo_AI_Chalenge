"""Toán khoảng ngày thuần dương lịch — không phụ thuộc lịch âm."""
from __future__ import annotations

from datetime import date, timedelta


def today(as_of: date) -> tuple[date, date]:
    return (as_of, as_of)


def n_days_ago(as_of: date, n: int) -> tuple[date, date]:
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
