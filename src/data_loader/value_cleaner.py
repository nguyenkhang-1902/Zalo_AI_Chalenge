"""Rule thuần làm sạch giá trị cột: số có dấu phẩy ngăn nghìn, số lượng kèm đơn vị, ngày VN."""
from __future__ import annotations

import re
from datetime import date, datetime

_NUMERIC_RE = re.compile(r"^-?\d[\d,]*\.?\d*$")
_QTY_UNIT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*(\D+)$")
_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")
_RAW_RATIO_THRESHOLD = 0.9
_QTY_UNIT_MATCH_THRESHOLD = 0.5


def _to_number(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if _NUMERIC_RE.match(text):
        return float(text.replace(",", ""))
    return None


def clean_numeric_column(values: list) -> tuple[list, str]:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"
    parsed = [_to_number(v) for v in non_null]
    ok_ratio = sum(p is not None for p in parsed) / len(non_null)
    if ok_ratio < _RAW_RATIO_THRESHOLD:
        return list(values), "raw"
    return [_to_number(v) for v in values], "numeric"


def split_quantity_unit(values: list) -> tuple[list, list] | None:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return None
    matched = sum(
        1
        for v in non_null
        if not isinstance(v, (int, float)) and _QTY_UNIT_RE.match(str(v).strip())
    )
    if matched / len(non_null) < _QTY_UNIT_MATCH_THRESHOLD:
        return None

    numbers, units = [], []
    for v in values:
        if v is None or str(v).strip() == "":
            numbers.append(None)
            units.append(None)
        elif isinstance(v, (int, float)):
            numbers.append(float(v))
            units.append(None)
        else:
            m = _QTY_UNIT_RE.match(str(v).strip())
            if m:
                numbers.append(float(m.group(1)))
                units.append(m.group(2).strip())
            else:
                numbers.append(None)
                units.append(None)
    return numbers, units


def parse_vn_date_column(values: list) -> tuple[list, str]:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"

    def _parse_one(v) -> date | None:
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        text = str(v).strip()
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    parsed = [_parse_one(v) for v in non_null]
    ok_ratio = sum(p is not None for p in parsed) / len(non_null)
    if ok_ratio < _RAW_RATIO_THRESHOLD:
        return list(values), "raw"

    result = []
    for v in values:
        if v is None or str(v).strip() == "":
            result.append(None)
        else:
            parsed_v = _parse_one(v)
            result.append(parsed_v.isoformat() if parsed_v else None)
    return result, "date"
