# Feature Specification: Date & Calendar Resolver

**Feature Branch**: `002-date-calendar-resolver` | **Created**: 2026-10-30 | **Status**: 🚧 Draft

## User Scenarios & Testing (mandatory)

### User Story 1 - Đổi "cách nói thời gian" thành khoảng ngày cụ thể (Priority: P1)

Sub-project kế tiếp (`004-reasoning-agent`) đọc câu hỏi tiếng Việt + `rulebook.md` §2 "Thời gian",
tự xác định câu hỏi đang nhắc đến khái niệm thời gian nào (vd "tháng này", "7 ngày gần nhất",
"Tết năm 2024"), rồi gọi đúng 1 hàm Python thuần trong sub-project này với `as_of_date` (+ lịch
âm nếu cần) để lấy về khoảng ngày `(start, end)` cụ thể, dùng trực tiếp trong SQL/pandas. Sub-project
này **không tự đọc hiểu câu hỏi** — chỉ cung cấp bộ hàm tính toán ngày chính xác theo đúng định
nghĩa `rulebook.md` §2.

**Why this priority**: Nếu khoảng ngày tính sai, mọi câu trả lời số liệu phía sau sai theo, bất kể
reasoning agent có thông minh đến đâu — đây là nền tảng tiếp theo sau `001-data-loader`.

**Independent Test**: Gọi từng hàm trực tiếp bằng unit test với `as_of_date` cố định, so khớp
tay với định nghĩa trong `rulebook.md` §2 — không cần `004-reasoning-agent` tồn tại.

**Acceptance Scenarios**:

1. **Given** `as_of_date = 2026-10-30` (thứ Sáu), **When** gọi `this_week(as_of)`, **Then** trả về
   `(2026-10-26, 2026-10-30)` (thứ Hai của tuần chứa hôm nay đến hết hôm nay).
2. **Given** `as_of_date = 2026-10-30`, **When** gọi `last_week(as_of)`, **Then** trả về
   `(2026-10-19, 2026-10-25)` (cả tuần liền trước, thứ Hai đến Chủ nhật).
3. **Given** `as_of_date = 2026-03-31` (tháng này có 31 ngày), **When** gọi
   `comparable_last_month(as_of)`, **Then** trả về `(2026-02-01, 2026-02-28)` (tháng 2 không có
   ngày 31 → lấy đến hết tháng trước).
4. **Given** `as_of_date = 2026-10-30`, **When** gọi `n_days_ago(as_of, 7)`, **Then** trả về
   `(2026-10-24, 2026-10-30)` (7 ngày liền nhau, kể cả hôm nay, ngày cuối là hôm nay).
5. **Given** `calendar.csv` thật của `train/`, **When** gọi `tet_period(calendar_index, year=2024)`,
   **Then** trả về đúng `(2024-02-02, 2024-02-19)` — 23 tháng Chạp âm 2023 đến mùng 10 tháng Giêng
   âm 2024 — tra thẳng từ dữ liệu lịch âm thật trong file, không tính toán âm lịch tự chế.
6. **Given** `as_of_date` nằm **sau** tháng 3 của năm nay, **When** gọi
   `month_or_quarter_without_year(as_of, month=3)`, **Then** trả về tháng 3 của **năm nay**; nếu
   `as_of_date` nằm **trước** tháng 3 (tháng 3 chưa tới), trả về tháng 3 của **năm trước**.
7. **Given** giờ tạo đơn `10:30`, **When** gọi `shift_session(10)`, **Then** trả về `"sáng"`
   (06:00–13:59); giờ `15:00` trả về `"chiều"` (14:00–21:59); giờ `23:00` trả về `None` (ngoài 2 ca).

### Edge Cases

- ⚠️ `tet_period`/`comparable_before_tet` gọi với năm **không có trong** `calendar.csv` đang dùng
  (ngoài phạm vi lịch cung cấp) → trả `None`, không raise — đây là giới hạn dữ liệu, không phải
  lỗi gọi hàm, để `004-reasoning-agent` tự quyết định unanswerable.
- ⚠️ Input sai kiểu/giá trị vô lý cho hàm (vd `n_days_ago(as_of, n=-1)`, `month_of(month=13, ...)`)
  → MUST raise `ValueError` ngay, vì đây là lỗi ở code gọi (bug), không phải business case — fail
  nhanh để bắt bug lúc dev/eval, không âm thầm trả khoảng ngày sai.
- ⚠️ `load_calendar` đọc file thiếu cột bắt buộc (`date`, `lunar_day`, `lunar_month`, `lunar_year`)
  → MUST raise lỗi rõ ràng ngay lúc nạp, không fail trễ lúc gọi hàm cần lịch âm.
- ⚠️ Tháng/quý không ghi năm rơi đúng **hôm nay** (không "sau hôm nay") → tính là năm nay theo
  đúng chữ "không sau hôm nay" trong rulebook (biên bao gồm hôm nay).

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: Hệ thống MUST cung cấp hàm `today(as_of)` trả về khoảng ngày của chính ngày
  `as_of` (`(as_of, as_of)`), dùng cho "ngày X", "hôm nay", "hôm qua" (hôm qua = `as_of - 1 ngày`
  truyền thẳng làm `as_of` của hàm).
- **FR-002**: Hệ thống MUST cung cấp hàm `n_days_ago(as_of, n)` trả về N ngày liền nhau kể cả
  `as_of`, ngày cuối là `as_of`, theo đúng định nghĩa rulebook §2.
- **FR-003**: Hệ thống MUST cung cấp `this_week(as_of)` (thứ Hai của tuần chứa `as_of` đến hết
  `as_of`) và `last_week(as_of)` (cả tuần liền trước, thứ Hai đến Chủ nhật).
- **FR-004**: Hệ thống MUST cung cấp `month_of(month, year)` trả về cả tháng, từ ngày 1 đến hết
  ngày cuối tháng đó (không tương đối với `as_of`).
- **FR-005**: Hệ thống MUST cung cấp `this_month(as_of)` (ngày 1 đến hết `as_of`) và
  `comparable_last_month(as_of)` (ngày 1 tháng trước đến hết ngày trùng số với `as_of`; nếu tháng
  trước không có ngày đó thì đến hết tháng trước).
- **FR-006**: Hệ thống MUST cung cấp `year_to_date(as_of)` trả về từ 01/01 năm của `as_of` đến hết
  `as_of`.
- **FR-007**: Hệ thống MUST cung cấp `month_or_quarter_without_year(as_of, month=None, quarter=None)`
  tự chọn năm nay hoặc năm trước theo đúng quy tắc "không sau hôm nay → năm nay, sau hôm nay → năm
  trước"; quý tính theo dương lịch, mỗi quý 3 tháng từ tháng 1.
- **FR-008**: Hệ thống MUST cung cấp `load_calendar(csv_path)` nạp `calendar.csv` 1 lần thành
  `CalendarIndex` có thể tra `(lunar_day, lunar_month, lunar_year) → ngày dương`, dùng cho các hàm
  cần lịch âm; MUST raise lỗi rõ nếu thiếu cột bắt buộc.
- **FR-009**: Hệ thống MUST cung cấp `tet_period(calendar_index, year)` trả về khoảng ngày
  dương từ 23 tháng Chạp (âm `year-1`) đến hết mùng 10 tháng Giêng (âm `year`), tra trực tiếp từ
  `CalendarIndex`; trả `None` nếu năm đó ngoài phạm vi dữ liệu lịch. Không nhận `as_of` — khoảng
  Tết năm Y là cố định theo `year`, không phụ thuộc "hôm nay".
- **FR-010**: Hệ thống MUST cung cấp `comparable_before_tet(calendar_index, year)` trả về
  khoảng ngày có **cùng số ngày** với `tet_period` tương ứng, nằm ngay **trước** ngày 23 tháng
  Chạp của kỳ Tết đó — dùng cho câu hỏi "so với trước Tết".
- **FR-011**: Hệ thống MUST cung cấp `shift_session(hour)` trả về `"sáng"` (giờ 06–13),
  `"chiều"` (giờ 14–21), hoặc `None` (ngoài 2 khoảng) — lọc theo **giờ**, không phải ngày.
- **FR-012**: Mọi hàm trả khoảng ngày MUST trả kiểu `(start: date | None, end: date)` bằng
  `datetime.date` thuần Python — `start=None` nghĩa là "từ đầu dữ liệu" (dùng cho "đến hết ngày X"
  dựng trực tiếp bằng `(None, X)`, không cần hàm riêng).
- **FR-013**: Hệ thống MUST NOT tự đọc/parse câu hỏi tiếng Việt để suy luận khái niệm thời gian —
  trách nhiệm đó thuộc `004-reasoning-agent`; sub-project này chỉ nhận tham số đã xác định rõ
  (as_of_date, n, month, year...) và trả khoảng ngày.
- **FR-014**: Hệ thống MUST NOT đọc `calendar.csv` bằng đường dẫn cứng — `load_calendar` nhận
  path làm tham số, vì dataset (train/public_test/private_test) khác thư mục.

### Key Entities

- **CalendarIndex**: đại diện cho `calendar.csv` đã nạp — tra được ngày dương theo ngày âm, dùng
  nội bộ bởi các hàm liên quan Tết; không lộ cấu trúc file CSV ra ngoài module.

## 🎯 Success Criteria (mandatory)

- **SC-001**: Toàn bộ hàm trong bảng FR-001 đến FR-011 có unit test khớp tay với định nghĩa
  `rulebook.md` §2, chạy xanh.
- **SC-002**: `tet_period` và `comparable_before_tet` được kiểm bằng lịch âm **thật** lấy trực
  tiếp từ `calendar.csv` của `train/` (ít nhất 1 năm Tết thật, không bịa ngày âm lịch giả).
- **SC-003**: Không có logic rẽ nhánh theo `business_id` hoặc dataset cụ thể trong module.

## 💡 Assumptions

- `rulebook.md` §2 giống nhau giữa `train/` và `public_test/` (đã đối chiếu thật — giống nhau
  ngoại trừ `public_test/` có thêm 1 dòng "Trung bình mỗi ngày thứ X của kỳ", không thuộc phạm vi
  v1 này). `private_test` có thể có luật mới — nếu phát sinh hàm mới cần thêm, không phải sửa hàm
  cũ.
- "Trung bình mỗi ngày thứ X của kỳ" (đếm số ngày thứ X trong 1 kỳ) và ngữ nghĩa so sánh "quá
  N/trên N/từ N trở lên" (quy tắc `>` vs `>=`) **không** thuộc phạm vi sub-project này — đây là
  logic đếm/so sánh khi sinh SQL, không phải tính khoảng ngày; để `004-reasoning-agent` tự xử lý
  lúc cần.
- Input `as_of_date`, `month`, `year`, `n`... luôn do `004-reasoning-agent` cung cấp sau khi đã
  hiểu câu hỏi — sub-project này không validate "câu hỏi có hợp lý không", chỉ validate kiểu/giá
  trị tham số (xem Edge Cases).
