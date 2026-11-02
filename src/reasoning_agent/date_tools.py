"""Tool 1:1 với date_resolver — FR-003 (12 tool), FR-004 (query_end). shift_session không trả
start/end (hàm gốc không có khái niệm khoảng ngày) nên không áp guard query_end — xem Global
Constraints/plan "Đính chính lúc viết plan"."""
from __future__ import annotations

from datetime import date

from date_resolver import (
    CalendarIndex,
    comparable_before_tet,
    comparable_last_month,
    last_week,
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

from reasoning_agent.react_loop import ToolSpec

_EMPTY_PARAMS = {"type": "object", "properties": {}, "required": []}


def _range_result(pair: tuple[date, date] | None, as_of_date: date) -> dict:
    if pair is None:
        return {"start": None, "end": None, "query_end": None, "note": "không có dữ liệu lịch cho kỳ này"}
    start, end = pair
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "query_end": min(end, as_of_date).isoformat(),
    }


def build_date_tool_registry(calendar_index: CalendarIndex, as_of_date: date) -> dict[str, ToolSpec]:
    return {
        "today": ToolSpec(
            schema={"name": "today", "description": "Hôm nay (as_of_date).", "parameters": _EMPTY_PARAMS},
            handler=lambda: _range_result(today(as_of_date), as_of_date),
        ),
        "n_days_ago": ToolSpec(
            schema={
                "name": "n_days_ago",
                "description": "N ngày gần nhất, kể cả hôm nay là ngày cuối (rulebook §2).",
                "parameters": {
                    "type": "object",
                    "properties": {"n": {"type": "integer", "description": "số ngày, >= 1"}},
                    "required": ["n"],
                },
            },
            handler=lambda n: _range_result(n_days_ago(as_of_date, n), as_of_date),
        ),
        "this_week": ToolSpec(
            schema={
                "name": "this_week",
                "description": "Tuần này: thứ Hai của tuần chứa hôm nay đến hết hôm nay.",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(this_week(as_of_date), as_of_date),
        ),
        "last_week": ToolSpec(
            schema={
                "name": "last_week",
                "description": "Tuần trước: cả tuần liền trước, thứ Hai đến Chủ nhật.",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(last_week(as_of_date), as_of_date),
        ),
        "year_to_date": ToolSpec(
            schema={
                "name": "year_to_date",
                "description": "Từ 01/01 năm nay đến hết hôm nay.",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(year_to_date(as_of_date), as_of_date),
        ),
        "month_of": ToolSpec(
            schema={
                "name": "month_of",
                "description": "Tháng M/Y: cả tháng, từ ngày 1 đến hết ngày cuối tháng.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "integer", "description": "1-12"},
                        "year": {"type": "integer"},
                    },
                    "required": ["month", "year"],
                },
            },
            handler=lambda month, year: _range_result(month_of(month, year), as_of_date),
        ),
        "this_month": ToolSpec(
            schema={
                "name": "this_month",
                "description": "Tháng này: từ ngày 1 đến hết hôm nay.",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(this_month(as_of_date), as_of_date),
        ),
        "comparable_last_month": ToolSpec(
            schema={
                "name": "comparable_last_month",
                "description": "Tháng trước, cùng số ngày với hôm nay (hết tháng trước nếu tháng trước không có ngày đó).",
                "parameters": _EMPTY_PARAMS,
            },
            handler=lambda: _range_result(comparable_last_month(as_of_date), as_of_date),
        ),
        "month_or_quarter_without_year": ToolSpec(
            schema={
                "name": "month_or_quarter_without_year",
                "description": (
                    "Tháng M hoặc quý Q không ghi năm: của năm nay nếu không sau hôm nay, "
                    "sau hôm nay thì của năm trước. Truyền đúng 1 trong 2 tham số."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "integer", "description": "1-12, bỏ trống nếu dùng quarter"},
                        "quarter": {"type": "integer", "description": "1-4, bỏ trống nếu dùng month"},
                    },
                    "required": [],
                },
            },
            handler=lambda month=None, quarter=None: _range_result(
                month_or_quarter_without_year(as_of_date, month=month, quarter=quarter), as_of_date
            ),
        ),
        "shift_session": ToolSpec(
            schema={
                "name": "shift_session",
                "description": (
                    "Ca sáng (06:00-13:59) hoặc ca chiều (14:00-21:59) theo giờ tạo đơn. "
                    "Trả null nếu ngoài 2 ca."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"hour": {"type": "integer", "description": "giờ trong ngày, 0-23"}},
                    "required": ["hour"],
                },
            },
            handler=lambda hour: {"session": shift_session(hour)},
        ),
        "tet_period": ToolSpec(
            schema={
                "name": "tet_period",
                "description": (
                    "Dịp Tết năm âm Y: từ 23 tháng Chạp (năm âm Y-1) đến hết mùng 10 tháng Giêng "
                    "(năm âm Y), theo ngày dương, tra từ calendar.csv."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"year": {"type": "integer", "description": "năm âm lịch Y"}},
                    "required": ["year"],
                },
            },
            handler=lambda year: _range_result(tet_period(calendar_index, year), as_of_date),
        ),
        "comparable_before_tet": ToolSpec(
            schema={
                "name": "comparable_before_tet",
                "description": "Cùng số ngày ngay trước dịp Tết năm âm Y (để so sánh trước/sau Tết).",
                "parameters": {
                    "type": "object",
                    "properties": {"year": {"type": "integer", "description": "năm âm lịch Y"}},
                    "required": ["year"],
                },
            },
            handler=lambda year: _range_result(comparable_before_tet(calendar_index, year), as_of_date),
        ),
    }
