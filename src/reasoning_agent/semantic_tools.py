"""Semantic-layer tool (US2): tham số hoá các phép tổng hợp phổ biến, sinh SQL từ schema.json lúc
runtime. KHÔNG chứa tri thức ngành — trạng thái loại trừ/loại giao dịch do model chọn từ rulebook
(FR-004). Giá trị luôn bind bằng `?`, tên bảng/cột luôn kiểm với schema rồi mới quote."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from reasoning_agent.react_loop import ToolSpec

SEMANTIC_TOOL_GUIDE = """## Tool tổng hợp có sẵn (ưu tiên dùng thay cho viết SQL tự do)
- `aggregate`: sum/avg/min/max/count/count_distinct theo khoảng ngày [start, end] (gồm cả end),
  bộ lọc, nhóm theo, top-N (order + limit; `tie_break_column` xếp tăng dần khi bằng nhau). Tên
  bảng/cột đúng như danh sách trên; lỗi tên sẽ trả danh sách tên hợp lệ.
- `percent_change`: (current - previous) / |previous| * 100, làm tròn 2 chữ số.
Điều kiện lọc nghiệp vụ (trạng thái đơn loại trừ, loại giao dịch...) PHẢI chọn theo rulebook ở
trên. Chỉ dùng `run_sql` khi `aggregate` không diễn đạt được câu hỏi."""

_AGGS = {"sum", "avg", "min", "max", "count", "count_distinct"}
_COMPARE_OPS = {"=", "!=", ">", ">=", "<", "<=", "like"}
_LIST_OPS = {"in", "not_in"}


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def build_semantic_tools(schema: dict, conn) -> dict[str, ToolSpec]:
    columns_by_table = {t["table_name"]: [c["name"] for c in t["columns"]] for t in schema["tables"]}

    def check_table(table: str) -> str:
        if table not in columns_by_table:
            raise ValueError(f"table không tồn tại: {table!r}. Các table có: {sorted(columns_by_table)}")
        return _quote(table)

    def check_column(table: str, column: str) -> str:
        if column not in columns_by_table[table]:
            raise ValueError(f"cột {column!r} không có trong {table!r}. Các cột có: {columns_by_table[table]}")
        return _quote(column)

    def agg_expression(agg: str, value_column: str | None) -> str:
        if agg not in _AGGS:
            raise ValueError(f"agg không hợp lệ: {agg!r}, phải là 1 trong {sorted(_AGGS)}")
        if agg == "count":
            return "COUNT(*)" if value_column is None else f"COUNT({value_column})"
        if value_column is None:
            raise ValueError(f"agg={agg} cần value_column")
        if agg == "count_distinct":
            return f"COUNT(DISTINCT {value_column})"
        return f"{agg.upper()}({value_column})"

    def aggregate(
        table: str,
        agg: str,
        value_column: str | None = None,
        date_column: str | None = None,
        start: str | None = None,
        end: str | None = None,
        filters: list | None = None,
        group_by: list | None = None,
        order: str = "desc",
        limit: int | None = None,
        tie_break_column: str | None = None,
    ) -> dict:
        quoted_table = check_table(table)
        value = check_column(table, value_column) if value_column else None
        group_cols = [check_column(table, c) for c in (group_by or [])]

        where: list[str] = []
        params: list = []
        if (start or end) and not date_column:
            raise ValueError("start/end cần date_column")
        if date_column:
            quoted_date = check_column(table, date_column)
            if start:
                where.append(f"CAST({quoted_date} AS DATE) >= CAST(? AS DATE)")
                params.append(start)
            if end:
                where.append(f"CAST({quoted_date} AS DATE) <= CAST(? AS DATE)")
                params.append(end)
        for f in filters or []:
            column, op, operand = check_column(table, f["column"]), f["op"], f["value"]
            if op in _LIST_OPS:
                placeholders = ", ".join("?" for _ in operand)
                where.append(f"{column} {'IN' if op == 'in' else 'NOT IN'} ({placeholders})")
                params.extend(operand)
            elif op in _COMPARE_OPS:
                where.append(f"{column} {op.upper() if op == 'like' else op} ?")
                params.append(operand)
            else:
                raise ValueError(f"op không hợp lệ: {op!r}, phải là 1 trong {sorted(_COMPARE_OPS | _LIST_OPS)}")

        select = ", ".join(group_cols + [f"{agg_expression(agg, value)} AS value"])
        sql = f"SELECT {select} FROM {quoted_table}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        if group_cols:
            sql += " GROUP BY " + ", ".join(group_cols)
            if order not in ("asc", "desc"):
                raise ValueError("order phải là 'asc' hoặc 'desc'")
            sql += f" ORDER BY value {order.upper()}"
            if tie_break_column:
                sql += f", {check_column(table, tie_break_column)} ASC"
        if limit is not None:
            if int(limit) < 1:
                raise ValueError("limit phải >= 1")
            sql += f" LIMIT {int(limit)}"

        result = conn.execute(sql, params)
        columns = [d[0] for d in result.description]
        rows = [[_jsonable(v) for v in row] for row in result.fetchall()]
        return {"columns": columns, "rows": rows, "sql": sql, "params": params}

    def percent_change(current: float, previous: float) -> dict:
        if previous == 0:
            raise ValueError("previous = 0, không tính được phần trăm thay đổi")
        return {"percent_change": round((current - previous) / abs(previous) * 100, 2)}

    return {
        "aggregate": ToolSpec(
            schema={
                "name": "aggregate",
                "description": "Tổng hợp 1 bảng: sum/avg/min/max/count/count_distinct, khoảng ngày, bộ lọc, nhóm theo, top-N.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string"},
                        "agg": {"type": "string", "enum": sorted(_AGGS)},
                        "value_column": {"type": "string"},
                        "date_column": {"type": "string"},
                        "start": {"type": "string", "description": "yyyy-mm-dd, gồm cả ngày start"},
                        "end": {"type": "string", "description": "yyyy-mm-dd, gồm cả ngày end"},
                        "filters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "op": {"type": "string", "enum": sorted(_COMPARE_OPS | _LIST_OPS)},
                                    "value": {},
                                },
                                "required": ["column", "op", "value"],
                            },
                        },
                        "group_by": {"type": "array", "items": {"type": "string"}},
                        "order": {"type": "string", "enum": ["asc", "desc"]},
                        "limit": {"type": "integer"},
                        "tie_break_column": {"type": "string"},
                    },
                    "required": ["table", "agg"],
                },
            },
            handler=aggregate,
        ),
        "percent_change": ToolSpec(
            schema={
                "name": "percent_change",
                "description": "(current - previous) / |previous| * 100, làm tròn 2 chữ số.",
                "parameters": {
                    "type": "object",
                    "properties": {"current": {"type": "number"}, "previous": {"type": "number"}},
                    "required": ["current", "previous"],
                },
            },
            handler=percent_change,
        ),
    }
