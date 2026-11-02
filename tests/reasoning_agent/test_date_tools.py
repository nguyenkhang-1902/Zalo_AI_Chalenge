from datetime import date
from pathlib import Path

from date_resolver import load_calendar
from reasoning_agent.date_tools import build_date_tool_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _registry(as_of_date: date):
    calendar_index = load_calendar(str(PROJECT_ROOT / "train" / "calendar.csv"))
    return build_date_tool_registry(calendar_index, as_of_date)


def test_registry_has_all_12_date_tools():
    registry = _registry(date(2026, 6, 16))
    assert set(registry) == {
        "today", "n_days_ago", "this_week", "last_week", "year_to_date",
        "month_of", "this_month", "comparable_last_month",
        "month_or_quarter_without_year", "shift_session",
        "tet_period", "comparable_before_tet",
    }


def test_today_returns_query_end_equal_to_as_of_date():
    registry = _registry(date(2026, 6, 16))
    result = registry["today"].handler()
    assert result == {"start": "2026-06-16", "end": "2026-06-16", "query_end": "2026-06-16"}


def test_month_of_query_end_cuts_at_as_of_when_month_still_ongoing():
    # month_of trả CẢ kỳ (cả tháng 6, FR-004) -- query_end phải CẮT tại as_of vì tháng chưa hết.
    registry = _registry(date(2026, 6, 16))
    result = registry["month_of"].handler(month=6, year=2026)
    assert result["end"] == "2026-06-30"
    assert result["query_end"] == "2026-06-16"


def test_month_of_query_end_equals_end_when_month_already_fully_past():
    registry = _registry(date(2026, 6, 16))
    result = registry["month_of"].handler(month=3, year=2026)
    assert result["end"] == "2026-03-31"
    assert result["query_end"] == "2026-03-31"


def test_n_days_ago_counts_today_as_day_1():
    registry = _registry(date(2026, 6, 16))
    result = registry["n_days_ago"].handler(n=7)
    assert result == {"start": "2026-06-10", "end": "2026-06-16", "query_end": "2026-06-16"}


def test_shift_session_returns_session_label_not_date_range():
    registry = _registry(date(2026, 6, 16))
    assert registry["shift_session"].handler(hour=8) == {"session": "sáng"}
    assert registry["shift_session"].handler(hour=22) == {"session": None}


def test_tet_period_uses_real_calendar_csv_and_cuts_query_end_mid_period():
    registry = _registry(date(2026, 2, 15))
    result = registry["tet_period"].handler(year=2026)
    assert result["start"] == "2026-02-10"
    assert result["end"] == "2026-02-26"
    assert result["query_end"] == "2026-02-15"


def test_tet_period_returns_note_when_year_not_in_calendar():
    registry = _registry(date(2026, 6, 16))
    result = registry["tet_period"].handler(year=1900)
    assert result == {
        "start": None, "end": None, "query_end": None,
        "note": "không có dữ liệu lịch cho kỳ này",
    }


def test_month_or_quarter_without_year_raises_when_both_given_lets_exception_propagate():
    # date_resolver.month_or_quarter_without_year tự raise ValueError khi truyền cả 2 -- date_tools
    # KHÔNG tự bắt (dispatch wrapper của react_loop ở Task 5 mới là nơi bắt chung).
    registry = _registry(date(2026, 6, 16))
    try:
        registry["month_or_quarter_without_year"].handler(month=3, quarter=1)
        assert False, "phải raise ValueError"
    except ValueError:
        pass
