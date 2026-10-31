# C5 Hardening — 001-data-loader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sửa 8 lỗi/finding hoãn lại từ final whole-branch review của `001-data-loader`
(checklist item C5), trước khi brainstorm `004-reasoning-agent`.

**Architecture:** Đây KHÔNG phải tính năng mới — là 1 đợt hardening/bugfix cho code đã có sẵn
trong `src/data_loader/`. Mỗi finding sửa đúng 1-2 file, không đổi kiến trúc tổng thể (README →
header-locate → clean → group → DuckDB + schema summary). 6/8 finding có fix code thật (#1, #2,
#3, #5, #6, #7, #8 — #1+#2 gộp 1 task vì cùng đụng `parse_vn_date_column`); 1 finding (#4) không
sửa code, chỉ verify lại sau khi #3 xong; task cuối chạy lại toàn bộ pipeline thật để xác nhận
không có regression.

**Tech Stack:** Python, pandas, DuckDB, openpyxl, pytest (giống `001-data-loader` gốc).

**Spec:** `specs/001-data-loader/spec.md` (không có spec mới — plan này sửa code để khớp ĐÚNG
spec gốc đã duyệt, không thêm yêu cầu nghiệp vụ mới). Nguồn yêu cầu trực tiếp của plan này là
bảng 8 finding đã được Khang duyệt ("ok đã ổn", 2026-10-31) — chép lại ở mục "Bối cảnh 8 Finding"
dưới đây, cùng root cause đã xác nhận bằng cách đọc source code + dữ liệu thật.

## Global Constraints

Copy verbatim từ `.specify/memory/constitution.md` — áp dụng cho MỌI task dưới đây:

- **Điều 1 (Đơn giản & dùng tính năng sẵn có)**: KISS/YAGNI, ưu tiên DuckDB/pandas/stdlib, không
  thêm thư viện mới cho các fix này.
- **Điều 2 (Nghiệm thu rõ ràng)**: không báo "xong" nếu chỉ "code chạy không lỗi" — mỗi task
  phải có test chạy thật PASS, task cuối phải có số liệu cụ thể (số table, warning count...).
- **Điều 3 (Đặt tên nhất quán)**: code Python `snake_case`; tên cột/table DuckDB giữ nguyên
  tiếng Việt có dấu từ README, không dịch/bỏ dấu.
- **Điều 4 (Hằng số thay magic value)**: ngưỡng mới (nếu cần) phải là hằng số module-level có
  tên rõ nghĩa, không hard-code rải trong logic — ưu tiên TÁI DÙNG hằng số đã có
  (`_RAW_RATIO_THRESHOLD`) khi cùng ý nghĩa, không tạo hằng số trùng lặp.
- **Điều 5 (Kỷ luật cấu trúc)**: không tách file mới trừ khi thật cần — các fix này đủ nhỏ để
  nằm trong file hiện có, không vượt trần 700 dòng/file sau khi sửa.
- **Điều 7 (Thiết kế cho quy mô & suy giảm duyên dáng)**: 1 file/sheet lỗi không được làm sập cả
  business — mọi fix PHẢI giữ nguyên hành vi try/except bao ngoài đã có (`build_business`'s
  per-group/per-sheet try/except), không bỏ guard nào đang tồn tại.
- **Điều 9 (Output rõ ràng, reproducible)**: không thêm phần ngẫu nhiên; chạy lại 2 lần phải ra
  kết quả giống nhau 100% (SC-004 của spec gốc vẫn phải giữ đúng sau khi sửa).
- **Điều 11 (Giữ nguyên ngữ cảnh tiếng Việt)**: không chuẩn hoá mất dấu/mất nghĩa dữ liệu
  tiếng Việt (áp dụng trực tiếp cho Finding #6 — số điện thoại/MST không phải là "số" theo nghĩa
  toán học, giữ dạng text đúng bản chất nghiệp vụ VN).

Từ `specs/001-data-loader/spec.md`:
- **FR-004**: chuẩn hoá số có dấu phẩy ngăn nghìn — fix Finding #6 KHÔNG được làm hỏng rule này
  cho cột số thật (vd `"51,000"` vẫn phải ra `51000.0`).
- **FR-011 / SHOULD liên quan**: hợp nhất file/sheet cùng schema bị chia theo kỳ thành 1 table
  UNION — Finding #5 là MỞ RỘNG trực tiếp của FR-011 (theo SHEET trong 1 file, không chỉ theo
  FILE).
- **SC-001**: chạy loader trên toàn bộ `train/data/` không business nào crash hoàn toàn (≥1
  table hợp lệ/business) — task cuối (Task 8) phải re-verify nguyên vẹn.
- **SC-004**: chạy lại cùng input 2 lần → kết quả giống nhau 100% — mọi fix không được phá vỡ
  idempotency.

## Bối cảnh 8 Finding (đã Khang duyệt 2026-10-31, root cause xác nhận bằng source code + dữ liệu thật)

| # | Vấn đề | Root cause | File đụng |
|---|---|---|---|
| 1 | Giờ trong ngày bị cắt mất | `parse_vn_date_column`'s `_parse_one` luôn gọi `.date()` khi gặp `datetime` object (openpyxl TỰ parse cell Excel có giờ thành `datetime.datetime` object thật — đã verify bằng scan thật trên `train/data/biz_105/SoBanHang_1.xlsx`, sheet "Thang 02 2025": `datetime.datetime(2025, 2, 1, 6, 0, 25)` v.v. — không phải text cần parse thêm format) | `value_cleaner.py` |
| 2 | Cột "date" lưu VARCHAR trong DuckDB | `parse_vn_date_column` trả `.isoformat()` string thay vì object `date`/`datetime` thật — đã verify bằng thực nghiệm: DuckDB suy đúng `DATE`/`TIMESTAMP` khi cột pandas là object chứa `date`/`datetime` Python thật, suy `VARCHAR` khi là string | `value_cleaner.py` |
| 3 | Header-locator fallback chọn nhầm dòng caption | Fallback "dòng đầu tiên mọi cell không rỗng đều string" không phân biệt dòng CAPTION báo cáo (1 cell, dạng "TIÊU ĐỀ HOA" hoặc "Nhãn: giá trị") với dòng HEADER thật khi không có `expected_columns` tốt để so khớp — verify bằng dữ liệu thật `train/data/biz_118/Bảng kê phiếu giao hàng.xlsx` (2 dòng caption `("BẢNG KÊ PHIẾU GIAO HÀNG",)` + `("Kỳ báo cáo: toàn bộ",)` phía trên header thật) | `header_locator.py` |
| 4 | 7/44 README dạng văn xuôi | KHÔNG sửa code — đã đọc thật `train/data/biz_106/README.md` + `biz_124/README.md`: không hề liệt kê tên cột theo file. Chỉ cần verify lại sau khi #3 fix | (không sửa, chỉ verify) |
| 5 | Period-series theo SHEET trong 1 file chưa gộp | `_group_raw_period_series` bucket theo `(sheet_name, expected_columns)` nên sheet "T01_2025"/"T02_2025"... (tên khác nhau) không bao giờ vào cùng bucket; `group_same_schema_files` (post-clean) chỉ validate period theo hậu tố tên FILE, không theo tên SHEET — verify quét lại toàn bộ `.xlsx` thật: **15 business** bị ảnh hưởng (xem chi tiết Task 6) | `schema_grouping.py`, `build_business_db.py` |
| 6 | SĐT/MST mất số 0 đầu | `clean_numeric_column` ép cột toàn chữ số thành `float` bất kể có nghĩa ID hay không — verify dữ liệu thật `train/data/biz_108/DanhSachKhachHang.xlsx` cột "Điện thoại" (`"0933201672"` → hiện ép thành `933201672.0`, mất số 0) | `value_cleaner.py` |
| 7 | Trùng tên cột hiếm | `_build_header` dedupe exact-string, không casefold (DuckDB column identifier không phân biệt hoa/thường) | `build_business_db.py` |
| 8 | `Pandas4Warning` dựng DataFrame lệch độ dài | `_clean_sheet_to_table` (dòng 97) không pad/truncate row về đúng độ dài header trước khi dựng DataFrame — verify thực nghiệm bằng `pandas 3.1.0`: tái hiện đúng `Pandas4Warning` | `build_business_db.py` |

## Project Structure

### Source Code (đã có, chỉ sửa)
```
src/data_loader/
├── value_cleaner.py      # Task 1 (Finding #1+#2), Task 2 (Finding #6)
├── header_locator.py     # Task 3 (Finding #3)
├── build_business_db.py  # Task 4 (Finding #7), Task 5 (Finding #8), Task 6 (Finding #5, phần raw-merge)
└── schema_grouping.py    # Task 6 (Finding #5, phần post-clean merge)
```

### Tests (đã có, chỉnh/thêm)
```
tests/data_loader/
├── test_value_cleaner.py          # Task 1, Task 2
├── test_header_locator.py         # Task 3
├── test_build_business_db.py      # Task 4, Task 5
├── test_schema_grouping.py        # Task 6
├── test_build_business_db_golden.py  # Task 6 (golden, biz_102/biz_105/dev_014 thật), Task 7
└── test_build_all_golden.py       # Task 8 (re-verify SC-001 toàn bộ train/+public_test/ thật)
```

## ⚠️ Complexity Tracking

Không có vi phạm Constitution Check cần biện minh — mọi fix đều nằm trong file/module đã có,
không thêm dependency, không thêm engine mới.

---
