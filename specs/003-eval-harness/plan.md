# Implementation Plan: Eval Harness

**Branch**: `003-eval-harness` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

## Summary

Thư viện Python thuần chấm điểm `submission.jsonl` theo đúng `rulebook.md` §9: đọc
`questions.jsonl` + `answers.jsonl` (ground truth, chỉ có ở `train/`) + `submission.jsonl`, áp quy
tắc format + so khớp giá trị theo từng answer type (kể cả cấu trúc `alias` thật trong dữ liệu), trả
về `EvalReport` (tổng điểm + breakdown theo type/business). Kèm 1 CLI mỏng in report.

## Technical Context

**Language/Version**: Python 3.11 (dùng lại venv/`requirements.txt` đã có)
**Primary Dependencies**: chỉ `json`, `re`, `argparse`, `dataclasses` của stdlib — không thêm
  dependency mới
**Storage**: không ghi file nào (trừ khi người dùng tự redirect output CLI) — hàm thuần nhận/trả
  giá trị trong bộ nhớ
**Testing**: `pytest`; golden test dùng trực tiếp `train/questions.jsonl` + `train/answers.jsonl`
  thật (3000 câu) — không fixture giả cho test tổng thể
**Target Platform**: như các sub-project trước — dev Windows, có thể chạy tay trong lúc dev
  `004`/`005` (không cần đóng gói vào Docker nộp bài — xem Assumptions trong spec)
**Performance Goals**: không áp dụng (JSONL text, 3000 dòng, xong trong vài giây)
**Constraints**: không hard-code theo `business_id`/`question_id` cụ thể (rule 4 cuộc thi, trừ
  trong test); không raise cho lỗi chấm điểm hợp lệ (sai type/giá trị) — chỉ raise cho lỗi dữ liệu
  thật (id trùng trong submission, answers thiếu entry)
**Scale/Scope**: 8 answer type theo rulebook §9, ~12 hàm thuần

## 🏛️ Constitution Check

| Điều | Áp dụng |
|---|---|
| 1 — Đơn giản | Chỉ stdlib (`json`, `re`, `argparse`, `dataclasses`) — không thêm dependency |
| 3 — Đặt tên | Tên hàm tiếng Anh snake_case mô tả đúng khái niệm rulebook (`match_number`, `match_table`...) |
| 5 — Kỷ luật cấu trúc | Tách `matchers.py` (so khớp giá trị thuần) / `scoring.py` (đọc file + orchestrate) / `report.py` (cấu trúc kết quả) / `cli.py` (I/O dòng lệnh) — 4 trách nhiệm rõ |
| 7 — Suy giảm duyên dáng | Dòng JSON hỏng trong submission → tính 0 điểm, không crash cả file; type sai → -1, không raise |
| 9 — Reproducibility | 100% tất định — không `random`, không LLM, không đọc giờ hệ thống |
| 10 — Luật cuộc thi | Không `business_id`/`question_id` nào trong logic rẽ nhánh — chỉ trong golden test |

Không có vi phạm cần biện minh → bỏ qua Complexity Tracking.

## Project Structure

### Documentation (this feature)
```
specs/003-eval-harness/{spec.md, plan.md, tasks.md}
```

### Source Code (repository root)
```
src/eval_harness/
  __init__.py       # export score_submission, EvalReport, TypeBreakdown, format_report
  matchers.py        # so khớp giá trị thuần theo type: match_number, match_percent, match_date,
                       # match_boolean, match_string, match_list, match_table,
                       # match_unanswerable, is_correct (dispatcher)
  report.py           # TypeBreakdown, EvalReport (dataclass), format_report()
  scoring.py           # _load_jsonl, _load_submission, score_submission()
  cli.py                # argparse wrapper gọi score_submission() + format_report()
tests/eval_harness/
  test_matchers.py             # unit test từng matcher, có ví dụ thật từ train/answers.jsonl
  test_report.py                # TypeBreakdown/EvalReport/format_report
  test_scoring_golden.py         # golden test: toàn bộ train/ thật (3000 câu) + các case lỗi
  test_package_exports.py        # import từ package root
```

Không có mục "Để sau" — spec này không có SHOULD/khoan nào bị giãn ưu tiên.
