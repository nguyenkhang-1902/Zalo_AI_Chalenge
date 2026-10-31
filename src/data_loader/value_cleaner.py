"""Rule thuần làm sạch giá trị cột: số có dấu phẩy ngăn nghìn, tiền VN có hậu tố, số lượng kèm đơn
vị, ngày VN. Giá trị thiếu phải là None (caller tự chuẩn hoá NaN/NaT của pandas về None)."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

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


def _looks_like_leading_zero_code(non_null: list) -> bool:
    """SĐT/MST VN quy ước giữ số 0 đầu (vd "0933201672") -- không ai viết số lượng/tiền (số
    nguyên hoặc thập phân) có số 0 đệm đầu, nên tỉ lệ cao giá trị dạng text bắt đầu bằng "0"
    (độ dài > 1, không phải số thập phân) là tín hiệu đủ mạnh để coi cả cột là mã định danh,
    không ép numeric. Tính tỉ lệ trên TOÀN BỘ non_null (không chỉ phần text), để 1 giá trị lệch
    hiếm trong 1 cột số nguyên-type thật không kéo cả cột về "raw"."""
    texts = [str(v).strip() for v in non_null if not isinstance(v, (int, float))]
    if not texts:
        return False
    zero_prefixed = sum(
        1 for t in texts if t.startswith("0") and len(t) > 1 and "." not in t and "," not in t
    )
    return zero_prefixed / len(non_null) >= _RAW_RATIO_THRESHOLD


def clean_numeric_column(values: list) -> tuple[list, str]:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"
    if _looks_like_leading_zero_code(non_null):
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


# Dấu chấm ngăn nghìn chỉ được coi là ngăn nghìn khi đi kèm hậu tố tiền tệ (đ/vnd/đồng) -- đây là
# tín hiệu tách bạch với số thập phân dấu chấm mà clean_numeric_column đang xử lý.
_MONEY_CURRENCY_RE = re.compile(r"^(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:đ|vnđ|vnd|đồng)$", re.IGNORECASE)
_MONEY_SCALED_RE = re.compile(r"^(\d+(?:,\d+)?)\s*(k|tr|triệu)$", re.IGNORECASE)
# "5tr520" = 5.520.000: đã đối chiếu SL x đơn giá = thành tiền trên dữ liệu thật. Chỉ nhận đúng 3
# chữ số sau "tr"; dạng "1tr2"/"1tr25" (mơ hồ: 1.200.000 hay 1.002.000?) cố ý KHÔNG match -> rơi
# xuống ngưỡng raw thay vì đoán sai.
_MONEY_TR_COMPOUND_RE = re.compile(r"^(\d+)\s*tr\s*(\d{3})$", re.IGNORECASE)
_MONEY_MULTIPLIERS = {"k": 1_000, "tr": 1_000_000, "triệu": 1_000_000}


def _to_money(value) -> float | None:
    """Số tiền có hậu tố VN -> float (giữ dấu âm của dòng trả hàng); None nếu không phải dạng
    tiền có hậu tố."""
    if value is None or isinstance(value, (int, float)):
        return None
    text = str(value).strip()
    sign = -1 if text.startswith("-") else 1
    text = text.lstrip("-").strip()
    m = _MONEY_CURRENCY_RE.match(text)
    if m:
        return sign * float(m.group(1).replace(".", ""))
    m = _MONEY_SCALED_RE.match(text)
    if m:
        amount = Decimal(m.group(1).replace(",", "."))
        return sign * float(amount * _MONEY_MULTIPLIERS[m.group(2).lower()])
    m = _MONEY_TR_COMPOUND_RE.match(text)
    if m:
        return sign * float(int(m.group(1)) * 1_000_000 + int(m.group(2)) * 1_000)
    return None


def parse_vn_money(values: list) -> tuple[list, str]:
    """Cột tiền viết tay kiểu VN ("1.500đ", "79k", "2,76tr", "5tr520") trộn số thường -> "numeric".
    Chỉ nhận khi có ít nhất 1 giá trị mang hậu tố tiền và >= _RAW_RATIO_THRESHOLD giá trị non-null
    là tiền-có-hậu-tố hoặc số thường; ngược lại trả "raw" để pipeline thử tiếp các rule khác."""
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"
    money = [_to_money(v) for v in non_null]
    if not any(m is not None for m in money):
        return list(values), "raw"
    ok = sum(m is not None or _to_number(v) is not None for m, v in zip(money, non_null))
    if ok / len(non_null) < _RAW_RATIO_THRESHOLD:
        return list(values), "raw"

    def _parse_one(v):
        m = _to_money(v)
        return m if m is not None else _to_number(v)

    return [_parse_one(v) for v in values], "numeric"


def parse_vn_date_column(values: list) -> tuple[list, str]:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"

    def _parse_one(v) -> date | datetime | None:
        if isinstance(v, datetime):
            return v
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

    # 1 giá trị có giờ/phút/giây thật (khác 00:00:00) đủ để nâng CẢ CỘT lên "datetime" -- giữ
    # đồng nhất 1 kiểu dữ liệu cho cả cột thay vì lẫn date/datetime từng dòng.
    has_time = any(
        isinstance(p, datetime) and (p.hour or p.minute or p.second) for p in parsed if p is not None
    )

    result = []
    for v in values:
        if v is None or str(v).strip() == "":
            result.append(None)
            continue
        parsed_v = _parse_one(v)
        if parsed_v is None:
            result.append(None)
        elif has_time:
            result.append(
                parsed_v if isinstance(parsed_v, datetime) else datetime(parsed_v.year, parsed_v.month, parsed_v.day)
            )
        else:
            result.append(parsed_v.date() if isinstance(parsed_v, datetime) else parsed_v)
    return result, "datetime" if has_time else "date"
