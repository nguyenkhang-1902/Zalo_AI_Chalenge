# Implementation Plan: Date & Calendar Resolver

**Branch**: `002-date-calendar-resolver` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

## Summary

Bộ hàm Python thuần, tất định, không phụ thuộc business cụ thể: nhận `as_of_date` (+ `CalendarIndex`
đã nạp từ `calendar.csv` cho các hàm cần lịch âm) và trả về `(start: date | None, end: date)` theo
đúng định nghĩa `rulebook.md` §2. Tách 2 module theo trách nhiệm: `date_resolver.py` (toán ngày
thuần dương lịch, không cần lịch âm) và `tet.py` (phụ thuộc `CalendarIndex`, tra lịch âm thật).

## Technical Context

**Language/Version**: Python 3.11 (dùng lại venv/`requirements.txt` đã có từ `001-data-loader`)
**Primary Dependencies**: chỉ `datetime`, `calendar`, `csv` của stdlib — không thêm dependency mới
**Storage**: không ghi file nào — module thuần hàm, nhận/trả giá trị trong bộ nhớ
**Testing**: `pytest`; test lịch âm dùng trực tiếp `train/calendar.csv` thật (không fixture giả)
**Target Platform**: như `001-data-loader` — dev Windows, chạy trong Docker offline ở sub-project 006
**Performance Goals**: không áp dụng (toán ngày thuần, tốc độ không đáng kể so với I/O của 001/004)
**Constraints**: không hard-code theo `business_id`/dataset cụ thể (rule 4 cuộc thi); không tự
  parse câu hỏi tiếng Việt (FR-013 — trách nhiệm của `004-reasoning-agent`)
**Scale/Scope**: ~12 hàm thuần theo spec FR-001 → FR-011, 1 `CalendarIndex` nạp 1 lần/lần gọi

## 🏛️ Constitution Check

| Điều | Áp dụng |
|---|---|
| 1 — Đơn giản | Chỉ stdlib (`datetime`, `calendar`, `csv`) — không thêm dependency; không viết hàm riêng cho `(None, X)` vì đó chỉ là tuple dựng trực tiếp (YAGNI) |
| 3 — Đặt tên | Tên hàm tiếng Anh snake_case mô tả đúng khái niệm rulebook (`tet_period`, `comparable_last_month`...) |
| 4 — Hằng số | `REQUIRED_COLUMNS` của `calendar.csv` là constant trong `calendar_index.py`, không lặp chuỗi cột rời rạc |
| 5 — Kỷ luật cấu trúc | Tách `date_resolver.py` (toán ngày thuần) khỏi `tet.py` (phụ thuộc lịch âm) — 2 trách nhiệm rõ, cả hai dưới 150 dòng |
| 7 — Suy giảm duyên dáng | `tet_period`/`comparable_before_tet` trả `None` khi năm ngoài phạm vi `calendar.csv`, không raise, không crash batch 004 |
| 9 — Reproducibility | 100% tất định — không `random`, không LLM, không đọc giờ hệ thống (mọi hàm nhận `as_of` làm tham số) |
| 10 — Luật cuộc thi | Không `business_id`/`question_id` nào trong logic — module không biết gì về business |

Không có vi phạm cần biện minh → bỏ qua Complexity Tracking.

## Project Structure

### Documentation (this feature)
```
specs/002-date-calendar-resolver/{spec.md, plan.md, tasks.md}
```

### Source Code (repository root)
```
src/date_resolver/
  __init__.py          # export công khai toàn bộ hàm/class dùng bởi 004-reasoning-agent
  calendar_index.py    # CalendarIndex, load_calendar(csv_path) — nạp calendar.csv 1 lần
  date_resolver.py      # today, n_days_ago, this_week, last_week, year_to_date,
                         # month_of, this_month, comparable_last_month,
                         # month_or_quarter_without_year, shift_session
  tet.py                 # tet_period, comparable_before_tet (phụ thuộc CalendarIndex)
tests/date_resolver/
  test_calendar_index.py        # load_calendar + tra lịch âm thật từ train/calendar.csv
  test_date_resolver_day_week.py # today/n_days_ago/this_week/last_week/year_to_date
  test_date_resolver_month.py    # month_of/this_month/comparable_last_month/
                                   # month_or_quarter_without_year/shift_session
  test_tet.py                     # tet_period/comparable_before_tet, dữ liệu Tết 2024 thật
  test_package_exports.py         # import từ package root, đối chiếu đủ FR-001..FR-011
```

Không có mục "Để sau" — spec này không có SHOULD/khoan nào bị giãn ưu tiên.
