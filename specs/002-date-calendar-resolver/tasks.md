# Tasks: Date & Calendar Resolver

> REQUIRED SUB-SKILL khi thực thi: `superpowers:subagent-driven-development` (khuyến nghị) hoặc
> `superpowers:executing-plans`. Mỗi task kết thúc bằng bước chạy test thật, không coi "xong" khi
> chưa thấy PASS.

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Global Constraints (áp dụng mọi task)

- Không `business_id`/`question_id`/dataset cụ thể nào trong logic rẽ nhánh (rule 4 cuộc thi).
- Chỉ dùng stdlib (`datetime`, `calendar`, `csv`) — không thêm dependency mới vào `requirements.txt`.
- Mọi hàm trả khoảng ngày MUST trả `tuple[date | None, date]` bằng `datetime.date` thuần — không
  trả string, không trả `None` cho `end`.
- Input sai kiểu/giá trị vô lý (n<1, month ngoài 1-12, quarter ngoài 1-4, hour ngoài 0-23) MUST
  raise `ValueError`. Năm ngoài phạm vi `calendar.csv` (chỉ áp dụng `tet_period`/`comparable_before_tet`)
  MUST trả `None`, không raise.
- Dùng lại venv + `requirements.txt`/`pytest.ini` đã có từ `001-data-loader` (không tạo venv mới).
- Test liên quan lịch âm MUST dùng trực tiếp `train/calendar.csv` thật, không fixture bịa ra.

---

## Phase 1: Calendar foundation

### Task 1: T001 [P] `calendar_index.py` — nạp calendar.csv

**Files:**
- Create: `src/date_resolver/__init__.py` (file rỗng — tạo ở task này để package import được, nội dung export đầy đủ thêm ở Task 5)
- Create: `src/date_resolver/calendar_index.py`
- Test: `tests/date_resolver/test_calendar_index.py`

**Interfaces:**
- Produces: `CalendarIndex` (dataclass, field `lunar_to_solar: dict[tuple[int,int,int], date]` —
  khóa `(lunar_day, lunar_month, lunar_year)`), `load_calendar(csv_path: str) -> CalendarIndex`.
  Task 4 (`tet.py`) tiêu thụ cả hai.

- [ ] **Step 1: Viết test trước — tra lịch âm thật + lỗi thiếu cột**

```python
# tests/date_resolver/test_calendar_index.py
from datetime import date
from pathlib import Path

import pytest

from date_resolver.calendar_index import load_calendar

REAL_CALENDAR = Path(__file__).resolve().parents[2] / "train" / "calendar.csv"


def test_looks_up_real_lunar_date_for_mung_1_tet_2024():
    index = load_calendar(str(REAL_CALENDAR))

    assert index.lunar_to_solar[(1, 1, 2024)] == date(2024, 2, 10)


def test_looks_up_real_lunar_date_for_23_thang_chap_2023():
    index = load_calendar(str(REAL_CALENDAR))

    assert index.lunar_to_solar[(23, 12, 2023)] == date(2024, 2, 2)


def test_missing_required_column_raises_value_error(tmp_path):
    bad_csv = tmp_path / "calendar.csv"
    bad_csv.write_text("date,weekday,holiday\n2024-01-01,1,Tết Dương lịch\n", encoding="utf-8")

    with pytest.raises(ValueError, match="thiếu cột"):
        load_calendar(str(bad_csv))
```

- [ ] **Step 2: Chạy test, xác nhận FAIL** (module chưa tồn tại)

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_calendar_index.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'date_resolver'`

- [ ] **Step 3: Tạo `src/date_resolver/__init__.py` rỗng**

```python
```

- [ ] **Step 4: Viết `src/date_resolver/calendar_index.py`**

```python
"""Nạp calendar.csv thành chỉ mục tra ngày âm -> ngày dương."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date

REQUIRED_COLUMNS = ("date", "lunar_day", "lunar_month", "lunar_year")


@dataclass
class CalendarIndex:
    lunar_to_solar: dict[tuple[int, int, int], date] = field(default_factory=dict)


def load_calendar(csv_path: str) -> CalendarIndex:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing = [col for col in REQUIRED_COLUMNS if col not in fieldnames]
        if missing:
            raise ValueError(f"calendar.csv thiếu cột bắt buộc: {missing}")

        index: dict[tuple[int, int, int], date] = {}
        for row in reader:
            solar_date = date.fromisoformat(row["date"])
            key = (
                int(row["lunar_day"]),
                int(row["lunar_month"]),
                int(row["lunar_year"]),
            )
            index[key] = solar_date

    return CalendarIndex(lunar_to_solar=index)
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_calendar_index.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/date_resolver/__init__.py src/date_resolver/calendar_index.py tests/date_resolver/test_calendar_index.py
git commit -m "feat(date-resolver): load calendar.csv into lunar-to-solar index"
```

---

## Phase 2: Pure date-math functions (không cần lịch âm)

### Task 2: T002 `date_resolver.py` phần A — ngày/tuần/từ-đầu-năm

**Files:**
- Create: `src/date_resolver/date_resolver.py`
- Test: `tests/date_resolver/test_date_resolver_day_week.py`

**Interfaces:**
- Produces: `today(as_of: date) -> tuple[date, date]`, `n_days_ago(as_of: date, n: int) -> tuple[date, date]`,
  `this_week(as_of: date) -> tuple[date, date]`, `last_week(as_of: date) -> tuple[date, date]`,
  `year_to_date(as_of: date) -> tuple[date, date]`. Task 3 thêm hàm vào cùng file này (không tạo lại).

- [ ] **Step 1: Viết test trước**

```python
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
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_date_resolver_day_week.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'date_resolver.date_resolver'`

- [ ] **Step 3: Viết `src/date_resolver/date_resolver.py` (phần A)**

```python
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
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_date_resolver_day_week.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/date_resolver/date_resolver.py tests/date_resolver/test_date_resolver_day_week.py
git commit -m "feat(date-resolver): add today/n_days_ago/this_week/last_week/year_to_date"
```

---

### Task 3: T003 `date_resolver.py` phần B — tháng/quý/ca làm việc

**Files:**
- Modify: `src/date_resolver/date_resolver.py` (thêm hàm vào file Task 2 đã tạo)
- Test: `tests/date_resolver/test_date_resolver_month.py`

**Interfaces:**
- Consumes: file `src/date_resolver/date_resolver.py` đã có `today/n_days_ago/this_week/last_week/year_to_date` từ Task 2 — chỉ thêm import `calendar` nếu cần, không sửa các hàm đã có.
- Produces: `month_of(month: int, year: int) -> tuple[date, date]`,
  `this_month(as_of: date) -> tuple[date, date]`,
  `comparable_last_month(as_of: date) -> tuple[date, date]`,
  `month_or_quarter_without_year(as_of: date, month: int | None = None, quarter: int | None = None) -> tuple[date, date]`,
  `shift_session(hour: int) -> str | None`. Task 5 import toàn bộ các hàm này vào `__init__.py`.

- [ ] **Step 1: Viết test trước**

```python
# tests/date_resolver/test_date_resolver_month.py
from datetime import date

import pytest

from date_resolver.date_resolver import (
    comparable_last_month,
    month_of,
    month_or_quarter_without_year,
    shift_session,
    this_month,
)


def test_month_of_returns_full_calendar_month():
    assert month_of(2, 2024) == (date(2024, 2, 1), date(2024, 2, 29))  # 2024 nhuận


def test_month_of_rejects_invalid_month():
    with pytest.raises(ValueError):
        month_of(13, 2024)


def test_this_month_from_day_1_to_today():
    assert this_month(date(2026, 10, 30)) == (date(2026, 10, 1), date(2026, 10, 30))


def test_comparable_last_month_same_day_number():
    assert comparable_last_month(date(2026, 10, 30)) == (date(2026, 9, 1), date(2026, 9, 30))


def test_comparable_last_month_clamps_when_previous_month_shorter():
    # tháng 3/2026 có 31 ngày, tháng 2/2026 chỉ có 28 -> lấy hết tháng 2
    assert comparable_last_month(date(2026, 3, 31)) == (date(2026, 2, 1), date(2026, 2, 28))


def test_comparable_last_month_wraps_year_at_january():
    assert comparable_last_month(date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 15))


def test_month_without_year_uses_this_year_when_not_future():
    # hôm nay 2026-10-30, hỏi "tháng 10" (đang diễn ra) -> năm nay
    assert month_or_quarter_without_year(date(2026, 10, 30), month=10) == (
        date(2026, 10, 1),
        date(2026, 10, 31),
    )


def test_month_without_year_uses_last_year_when_future():
    # hôm nay 2026-10-30, hỏi "tháng 11" (chưa tới) -> năm trước
    assert month_or_quarter_without_year(date(2026, 10, 30), month=11) == (
        date(2025, 11, 1),
        date(2025, 11, 30),
    )


def test_quarter_without_year_uses_this_year_when_not_future():
    # Q4 bắt đầu 01/10, hôm nay 30/10 -> đã bắt đầu -> năm nay
    assert month_or_quarter_without_year(date(2026, 10, 30), quarter=4) == (
        date(2026, 10, 1),
        date(2026, 12, 31),
    )


def test_month_or_quarter_requires_exactly_one_arg():
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30))
    with pytest.raises(ValueError):
        month_or_quarter_without_year(date(2026, 10, 30), month=5, quarter=2)


def test_shift_session_morning_afternoon_and_outside():
    assert shift_session(10) == "sáng"
    assert shift_session(15) == "chiều"
    assert shift_session(23) is None


def test_shift_session_rejects_invalid_hour():
    with pytest.raises(ValueError):
        shift_session(24)
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_date_resolver_month.py -v`
Expected: FAIL với `ImportError: cannot import name 'month_of' from 'date_resolver.date_resolver'`

- [ ] **Step 3: Thêm vào cuối `src/date_resolver/date_resolver.py`**

```python
import calendar as _cal_mod


def month_of(month: int, year: int) -> tuple[date, date]:
    if not 1 <= month <= 12:
        raise ValueError(f"month phải 1-12, got {month}")
    last_day = _cal_mod.monthrange(year, month)[1]
    return (date(year, month, 1), date(year, month, last_day))


def this_month(as_of: date) -> tuple[date, date]:
    return (date(as_of.year, as_of.month, 1), as_of)


def comparable_last_month(as_of: date) -> tuple[date, date]:
    if as_of.month == 1:
        prev_year, prev_month = as_of.year - 1, 12
    else:
        prev_year, prev_month = as_of.year, as_of.month - 1

    last_day_prev = _cal_mod.monthrange(prev_year, prev_month)[1]
    end_day = min(as_of.day, last_day_prev)
    return (date(prev_year, prev_month, 1), date(prev_year, prev_month, end_day))


def month_or_quarter_without_year(
    as_of: date, month: int | None = None, quarter: int | None = None
) -> tuple[date, date]:
    if (month is None) == (quarter is None):
        raise ValueError("phải truyền đúng 1 trong 2: month hoặc quarter")

    if month is not None:
        if not 1 <= month <= 12:
            raise ValueError(f"month phải 1-12, got {month}")
        start_month, end_month = month, month
    else:
        if not 1 <= quarter <= 4:
            raise ValueError(f"quarter phải 1-4, got {quarter}")
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2

    candidate_start = date(as_of.year, start_month, 1)
    year = as_of.year if candidate_start <= as_of else as_of.year - 1
    end_day = _cal_mod.monthrange(year, end_month)[1]
    return (date(year, start_month, 1), date(year, end_month, end_day))


def shift_session(hour: int) -> str | None:
    if not 0 <= hour <= 23:
        raise ValueError(f"hour phải 0-23, got {hour}")
    if 6 <= hour <= 13:
        return "sáng"
    if 14 <= hour <= 21:
        return "chiều"
    return None
```

**Import ở đầu file** (sau `from datetime import date, timedelta` đã có từ Task 2) — thêm
`import calendar as _cal_mod` ngay dưới, không đổi tên module gây nhầm với package `date_resolver`.

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_date_resolver_month.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add src/date_resolver/date_resolver.py tests/date_resolver/test_date_resolver_month.py
git commit -m "feat(date-resolver): add month/quarter-without-year and shift_session"
```

---

## Phase 3: Lunar/Tết (phụ thuộc CalendarIndex)

### Task 4: T004 `tet.py` — khoảng Tết + khoảng trước Tết

**Files:**
- Create: `src/date_resolver/tet.py`
- Test: `tests/date_resolver/test_tet.py`

**Interfaces:**
- Consumes: `CalendarIndex` từ `src/date_resolver/calendar_index.py` (Task 1) — field
  `lunar_to_solar: dict[tuple[int,int,int], date]`.
- Produces: `tet_period(calendar_index: CalendarIndex, year: int) -> tuple[date, date] | None`,
  `comparable_before_tet(calendar_index: CalendarIndex, year: int) -> tuple[date, date] | None`.
  Task 5 import cả hai vào `__init__.py`.

- [ ] **Step 1: Viết test trước — dùng `train/calendar.csv` thật, Tết âm 2024**

```python
# tests/date_resolver/test_tet.py
from datetime import date
from pathlib import Path

from date_resolver.calendar_index import load_calendar
from date_resolver.tet import comparable_before_tet, tet_period

REAL_CALENDAR = Path(__file__).resolve().parents[2] / "train" / "calendar.csv"


def test_tet_period_2024_matches_real_calendar():
    index = load_calendar(str(REAL_CALENDAR))

    # 23 tháng Chạp âm 2023 = 2024-02-02; mùng 10 tháng Giêng âm 2024 = 2024-02-19
    assert tet_period(index, 2024) == (date(2024, 2, 2), date(2024, 2, 19))


def test_tet_period_returns_none_when_year_out_of_calendar_range():
    index = load_calendar(str(REAL_CALENDAR))

    assert tet_period(index, 1990) is None


def test_comparable_before_tet_2024_has_same_length_right_before_23_thang_chap():
    index = load_calendar(str(REAL_CALENDAR))

    # tet_period dài 18 ngày (2024-02-02 -> 2024-02-19) -> 18 ngày ngay trước 2024-02-02
    assert comparable_before_tet(index, 2024) == (date(2024, 1, 15), date(2024, 2, 1))


def test_comparable_before_tet_returns_none_when_tet_period_is_none():
    index = load_calendar(str(REAL_CALENDAR))

    assert comparable_before_tet(index, 1990) is None
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_tet.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'date_resolver.tet'`

- [ ] **Step 3: Viết `src/date_resolver/tet.py`**

```python
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
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_tet.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/date_resolver/tet.py tests/date_resolver/test_tet.py
git commit -m "feat(date-resolver): add tet_period and comparable_before_tet from real calendar.csv"
```

---

## Phase 4: Package exports

### Task 5: T005 `__init__.py` — export công khai + test tích hợp

**Files:**
- Modify: `src/date_resolver/__init__.py` (file rỗng từ Task 1, điền export ở đây)
- Test: `tests/date_resolver/test_package_exports.py`

**Interfaces:**
- Consumes: toàn bộ hàm/class Public từ Task 1-4 (`calendar_index.py`, `date_resolver.py`, `tet.py`).
- Produces: `date_resolver` package — mọi hàm import trực tiếp từ `date_resolver` (không cần biết
  tên file con bên trong) — đây là bề mặt mà `004-reasoning-agent` sẽ gọi vào.

- [ ] **Step 1: Viết test trước — import thẳng từ package root**

```python
# tests/date_resolver/test_package_exports.py
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
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_package_exports.py -v`
Expected: FAIL với `ImportError: cannot import name 'CalendarIndex' from 'date_resolver'`

- [ ] **Step 3: Viết `src/date_resolver/__init__.py`**

```python
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
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/test_package_exports.py -v`
Expected: 1 passed

- [ ] **Step 5: Chạy toàn bộ test của sub-project này, xác nhận PASS hết**

Run: `.venv/Scripts/python -m pytest tests/date_resolver/ -v`
Expected: 26 passed (3 + 6 + 12 + 4 + 1)

- [ ] **Step 6: Commit**

```bash
git add src/date_resolver/__init__.py tests/date_resolver/test_package_exports.py
git commit -m "feat(date-resolver): export public API from package root"
```
