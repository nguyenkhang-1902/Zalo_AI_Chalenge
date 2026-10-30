# tests/date_resolver/test_date_resolver_day_week.py
from datetime import date

import pytest

from date_resolver.date_resolver import (
    last_week,
    n_days_ago,
    this_week,
    today,
    year_to_date,
)


def test_today_returns_the_single_day():
    assert today(date(2026, 10, 30)) == (date(2026, 10, 30), date(2026, 10, 30))


def test_n_days_ago_includes_today_as_last_day():
    assert n_days_ago(date(2026, 10, 30), 7) == (date(2026, 10, 24), date(2026, 10, 30))


def test_n_days_ago_rejects_non_positive_n():
    with pytest.raises(ValueError):
        n_days_ago(date(2026, 10, 30), 0)


def test_this_week_starts_monday_ends_today():
    # 2026-10-30 là thứ Sáu
    assert this_week(date(2026, 10, 30)) == (date(2026, 10, 26), date(2026, 10, 30))


def test_last_week_is_full_previous_monday_to_sunday():
    assert last_week(date(2026, 10, 30)) == (date(2026, 10, 19), date(2026, 10, 25))


def test_year_to_date_starts_jan_1_same_year():
    assert year_to_date(date(2026, 10, 30)) == (date(2026, 1, 1), date(2026, 10, 30))
