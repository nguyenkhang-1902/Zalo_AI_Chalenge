# Implementation Plan: Data Loader & Schema Layer

**Branch**: `001-data-loader` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

## Summary

Đọc `README.md` + file Excel/CSV thô của 1 business → tự định vị header, làm sạch số/ngày/đơn vị,
gộp file cùng schema bị chia theo kỳ (FR-011), ghi ra 1 file DuckDB/business + 1 schema summary
JSON. Chạy 1 lần/business, thuần rule-based (không LLM) để tất định + nhanh.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: `duckdb`, `pandas`, `openpyxl`, `pytest` (xem `requirements.txt`)
**Storage**: 1 file `.duckdb`/business + 1 file `.schema.json`/business, ghi vào `--out` do caller chỉ định
**Testing**: `pytest`, unit test cho từng module + golden test chạy trực tiếp trên `train/`+`public_test/` thật
**Target Platform**: dev trên Windows (laptop/máy công ty); sau này chạy trong Docker offline (sub-project 006)
**Performance Goals**: SC-003 — toàn bộ 30 business `train/` xong dưới 2 phút
**Constraints**: không hard-code theo `business_id` (rule 4 cuộc thi); không dùng LLM ở bước này (tất định, phục vụ rule 8 reproducibility)
**Scale/Scope**: 2–24+ file/business hiện tại; code phải tổng quát, không giả định số file cố định

## 🏛️ Constitution Check

| Điều | Áp dụng |
|---|---|
| 1 — Đơn giản | DuckDB/pandas/openpyxl, không Spark (đã quyết lúc brainstorm) |
| 3 — Đặt tên | Tên cột/table giữ tiếng Việt có dấu, quote identifier trong SQL (`duckdb_writer.py`) |
| 5 — Kỷ luật cấu trúc | Mỗi module 1 trách nhiệm, tất cả dưới 250 dòng (xem Project Structure) |
| 7 — Suy giảm duyên dáng | Mỗi sheet lỗi try/except riêng trong `build_business_db.py`, không crash cả business |
| 9 — Reproducibility | Không phần ngẫu nhiên nào trong cả pipeline A; test idempotent (T010) xác nhận |
| 10 — Luật cuộc thi | Không `business_id` nào xuất hiện trong logic rẽ nhánh — chỉ trong test fixtures/golden test |

Không có vi phạm cần biện minh → bỏ qua Complexity Tracking.

## Project Structure

### Documentation (this feature)
```
specs/001-data-loader/{spec.md, plan.md, tasks.md, checklists/requirements.md}
```

### Source Code (repository root)
```
requirements.txt
pytest.ini
src/data_loader/
  __init__.py
  models.py            # LoadedTable (dataclass dùng chung)
  sheet_reader.py       # đọc thô csv/xlsx
  readme_parser.py      # parse README.md -> cột khai báo/file
  header_locator.py     # định vị dòng header thật
  value_cleaner.py      # làm sạch số/ngày/số lượng-đơn vị
  schema_grouping.py    # FR-011: gộp file cùng schema chia theo kỳ
  schema_summary.py     # sinh JSON tóm tắt schema
  duckdb_writer.py       # ghi DuckDB
  build_business_db.py  # orchestrator 1 business + CLI
  build_all.py           # batch runner toàn dataset + copy rulebook/calendar + CLI
tests/
  test_setup.py
  data_loader/
    test_sheet_reader.py
    test_readme_parser.py
    test_header_locator.py
    test_value_cleaner.py
    test_schema_grouping.py
    test_schema_summary.py
    test_duckdb_writer.py
    test_build_business_db_golden.py   # chạy trên train/data/biz_105 + public_test/data/dev_005 thật
    test_build_all_golden.py           # chạy trên toàn bộ train/ thật, kiểm SC-001/SC-003
build_output/            # gitignored — nơi golden test thật ghi .duckdb/.schema.json khi chạy tay
```

## 🟡 Để sau (không vi phạm constitution, chỉ giãn ưu tiên vì deadline 16/11)

- **SHOULD-012** (gợi ý khoá liên kết giữa table): để sau `001-data-loader` nếu còn thời gian — không chặn sub-project `004-reasoning-agent`.
- **SC-002** (≥95% cột số/ngày quan trọng parse đúng): không viết test tự động riêng ở sub-project này — sẽ lộ ra tự nhiên qua accuracy thật khi ghép với `003-eval-harness`. Theo dõi thủ công qua `schema.json` lúc review.
