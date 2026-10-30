from datetime import date


def test_all_public_functions_importable_from_package_root():
    from date_resolver import (
        CalendarIndex,
        comparable_before_tet,
        comparable_last_month,
        last_week,
        load_calendar,
        month_of,
        month_or_quarter_without_year,
        n_days_ago,
        shift_session,
        tet_period,
        this_month,
        this_week,
        today,
        year_to_date,
    )

    assert today(date(2026, 10, 30)) == (date(2026, 10, 30), date(2026, 10, 30))
    assert CalendarIndex is not None
    assert load_calendar is not None
    assert tet_period is not None
    assert comparable_before_tet is not None
    assert all(
        [
            comparable_last_month,
            last_week,
            month_of,
            month_or_quarter_without_year,
            n_days_ago,
            shift_session,
            this_month,
            this_week,
            year_to_date,
        ]
    )
