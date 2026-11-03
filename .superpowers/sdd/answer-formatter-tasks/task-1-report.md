# Task 1 Report — `normalize_answer` (FR-008)

Sub-project: 005-answer-formatter. Brief: `task-1-brief.md`. Nhánh: `main` (làm trực tiếp, không branch/worktree).

## Các bước đã làm

1. Đọc brief, kiểm tra repo: branch `main`, working tree sạch, `pytest.ini` có `pythonpath = src`, `.venv` Python 3.11.9 + pytest 9.2.0.
2. **RED**: tạo `tests/answer_formatter/test_normalize.py` đúng nội dung brief (8 test). Chạy `.venv/Scripts/python.exe -m pytest tests/answer_formatter/test_normalize.py -v` → collection error, module chưa tồn tại.
3. **GREEN**: tạo `src/answer_formatter/normalize.py` đúng code brief; tạo 2 file `__init__.py` rỗng (`src/answer_formatter/__init__.py`, `tests/answer_formatter/__init__.py`). Chạy lại pytest → 8 passed.
4. Tự review (xem phần dưới).
5. Commit (xem phần cuối).

## Lệnh test và kết quả

- RED: `pytest tests/answer_formatter/test_normalize.py -v` → `ModuleNotFoundError: No module named 'answer_formatter.normalize'` (collection error, 0 test chạy).
- GREEN: `pytest tests/answer_formatter/test_normalize.py -v` → **8 passed in 0.02s**.

## Sai lệch so với brief

1. **Thông báo lỗi RED khác brief một chút**: brief kỳ vọng `No module named 'answer_formatter'`. Tôi đã `mkdir -p src/answer_formatter` trước khi chạy pytest RED nên Python tìm thấy package và chỉ báo thiếu `answer_formatter.normalize`. Vẫn là lỗi "module chưa tồn tại" đúng bản chất RED; không ảnh hưởng implementation.
2. **Force-add báo cáo**: `.superpowers/sdd/.gitignore` chứa `*`, nên `task-1-report.md` (và `task-1-brief.md`) đang bị ignore. Theo yêu cầu "commit báo cáo cùng code", báo cáo được `git add -f` riêng file này. Các file brief/progress khác trong thư mục vẫn không bị add.
3. Ngoài 4 file brief liệt kê, commit có thêm file báo cáo (theo yêu cầu người điều phối).

## Tự review

- Đúng spec brief: percent làm tròn 2 chữ số; bỏ qua `bool` và non-numeric; table map alias `cols→columns`, `data/records→rows`; key lạ giữ nguyên; type khác trả về nguyên object.
- Không mutate input: mọi nhánh trả về dict mới (`{**result, ...}`) hoặc chính `result` khi không đổi.
- **Concern (chưa sửa, nằm ngoài test của brief)**: nếu một table answer có đồng thời hai key cùng canonical (ví dụ `{"rows": ..., "data": ...}` hoặc `{"columns": ..., "cols": ...}`), dict comprehension sẽ **ghi đè âm thầm** một trong hai giá trị, phụ thuộc thứ tự key. Brief không yêu cầu xử lý trường hợp này và yêu cầu dùng đúng code; tôi giữ nguyên. Nếu Task 2 hoặc FR-008 cần, nên quyết định (raise / giữ canonical key ưu tiên) ở task sau.
- `percent` với `answer` là `float('nan')`/`inf`: `round` trả về nguyên giá trị, không báo lỗi. Ngoài phạm vi test, ghi nhận để biết.
- Không có lint/type-check nào trong repo cho task này được kiểm tra (chỉ chạy pytest).

## Commit

- Add (explicit list): `src/answer_formatter/__init__.py`, `src/answer_formatter/normalize.py`, `tests/answer_formatter/__init__.py`, `tests/answer_formatter/test_normalize.py`, và `git add -f .superpowers/sdd/answer-formatter-tasks/task-1-report.md`.
- Message: `feat: add answer_formatter.normalize_answer (FR-008)`, kèm dòng `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>`.
