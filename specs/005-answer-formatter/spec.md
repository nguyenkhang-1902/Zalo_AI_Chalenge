# Feature Specification: Answer Formatter

**Feature Branch**: `005-answer-formatter` | **Created**: 2026-11-03 | **Status**: 🚧 Draft

## User Scenarios & Testing (mandatory)

### User Story 1 - Chạy cả 1 bộ câu hỏi và xuất đúng file submission (Priority: P1)

Với 1 bộ dữ liệu (`train/` hoặc `public_test/`, sau này `private_test/`), hệ thống phải đọc hết
`questions.jsonl` của bộ đó, gọi `answer_question` (004) cho từng câu, chuẩn hoá đáp án theo đúng
format `rulebook.md` §9, rồi ghi ra 1 file `submission.jsonl` mà `score_submission` (003) đọc
được không lỗi — đây là input thật mà BTC cần (`006-docker-packaging` sẽ gọi lại đúng pipeline
này, chỉ đổi đường dẫn output thành `/result/submission.jsonl`).

**Why this priority**: Không có 005, mỗi lần muốn đo accuracy thật trên nhiều câu phải tự viết
script ad-hoc (đã từng làm vậy ở Task 7 của `004`) — không tái dùng được, không phải thứ nộp
Docker được. 005 là mảnh ghép bắt buộc để có 1 pipeline hoàn chỉnh từ input thật ra output thật.

**Independent Test**: Chạy CLI trên 1 mẫu nhỏ (5-10 câu lấy từ `train/questions.jsonl`,
`--dataset-dir train/`), ra `submission.jsonl`, chạy `score_submission` (003) trên file đó —
không lỗi format, có điểm số (dù thấp) — không cần `006-docker-packaging` tồn tại.

**Acceptance Scenarios**:

1. **Given** `submission.jsonl` chưa tồn tại và bộ câu hỏi có N dòng, **When** chạy batch,
   **Then** file output có đúng N dòng, mỗi dòng `{"id": ..., "type": ..., "answer": ...}` (hoặc
   `{"id": ..., "type": "unanswerable", "reason": ...}`) — đúng format `_load_submission` của 003
   đọc được, không trùng/thiếu `id`.
2. **Given** `--concurrency` > 1, **When** chạy batch, **Then** tất cả N dòng được ghi đúng 1 lần
   — không trùng, không mất dòng (xác minh bằng `answer_fn` giả tốc độ cao + nhiều worker).
3. **Given** file output đã có sẵn M dòng từ lượt chạy trước (bị dừng giữa chừng), **When** chạy
   lại đúng lệnh, **Then** M câu đã có bị bỏ qua (không gọi lại `answer_fn`), chỉ xử lý phần còn
   thiếu, cuối cùng đủ N dòng.
4. **Given** `answer_fn` raise exception cho 1 câu hỏi cụ thể (vd thiếu `rulebook.md` cho 1
   business lạ, timeout mạng), **When** batch chạy, **Then** dòng đó được ghi
   `{"type": "unanswerable", "reason": "lỗi xử lý: <mô tả>"}`, batch **tiếp tục** xử lý các câu
   còn lại, không dừng toàn bộ.
5. **Given** đáp án `type="percent"` với giá trị số thực chưa tròn (vd `12.398572`), **When**
   chuẩn hoá, **Then** ghi ra số đã tròn 2 chữ số thập phân (`12.4`).
6. **Given** đáp án `type="table"` với key nằm trong danh sách alias cố định (vd
   `{"cols": [...], "data": [[...]]}`), **When** chuẩn hoá, **Then** ghi ra đúng key
   `{"columns": ..., "rows": ...}`; **Given** key lạ ngoài alias, **When** chuẩn hoá, **Then**
   giữ nguyên không đổi (để sai — đúng tinh thần rulebook "sai format là sai", 005 không tự ý
   "cứu" dữ liệu sai dạng).
7. **Given** `--limit N` kèm resume (đã có M dòng cũ), **When** chạy batch, **Then** chỉ lấy N
   câu đầu tiên trong phần **chưa** resume-skip (N không tính các câu đã xong).

### Edge Cases

- ⚠️ `id` trùng lặp trong chính `questions.jsonl` đầu vào (lỗi dữ liệu, không phải case mong đợi
  từ BTC) → MUST raise lỗi rõ ràng ngay từ đầu, trước khi xử lý bất kỳ câu nào.
- ⚠️ File output cũ có dòng JSON hỏng/thiếu `"id"` → bỏ qua dòng đó khi tính resume-set (khoan
  dung, giống `_load_submission` của 003), không raise.
- ⚠️ Thư mục cha của `--out` chưa tồn tại → tự tạo (`mkdir -p` tương đương), không raise.
- ⚠️ `--concurrency` < 1 → raise lỗi validation ngay từ đầu, không chạy ngầm sai.
- ⚠️ `--limit 0` → chạy xong ngay không gọi `answer_fn` nào (hợp lệ — dùng để test nhanh pipeline
  không tốn thời gian gọi LLM).
- ⚠️ `answer_fn` trả về giá trị không đúng hợp đồng (không phải `dict`, hoặc thiếu `"type"`, hoặc
  thiếu `"answer"` khi `type != "unanswerable"`) → xử lý như lỗi (giống exception ở Acceptance
  Scenario 4), KHÔNG để lỗi hợp đồng này làm sập batch.

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: Hệ thống MUST cung cấp `run_batch(questions_path: Path, dataset_dir: Path,
  out_path: Path, concurrency: int = 1, limit: int | None = None, answer_fn: Callable[[str, str,
  date, Path], dict] = answer_question) -> BatchSummary` — `answer_fn` MUST nhận đúng 4 tham số
  (`question, business_id, as_of_date, dataset_dir`) khớp chữ ký thật của `answer_question` (004),
  và `run_batch` MUST truyền `dataset_dir` của chính nó vào mỗi lời gọi `answer_fn`.
- **FR-002**: `run_batch` MUST đọc `questions_path` (JSONL, mỗi dòng `{"id", "business_id",
  "question", "as_of_date"}`), parse `as_of_date` bằng `date.fromisoformat`.
- **FR-003**: Nếu `out_path` đã tồn tại, `run_batch` MUST đọc trước (khoan dung — bỏ dòng rỗng,
  JSON hỏng, hoặc thiếu `"id"`, không raise), lấy tập `id` đã có để loại khỏi hàng đợi xử lý
  (resume).
- **FR-004**: `run_batch` MUST hỗ trợ xử lý tối đa `concurrency` câu hỏi đồng thời
  (`ThreadPoolExecutor`); `concurrency=1` MUST cho kết quả tương đương xử lý tuần tự.
- **FR-005**: Mỗi câu hỏi xử lý xong (thành công hoặc lỗi) MUST được ghi ngay 1 dòng JSONL vào
  `out_path` (append + flush ngay), dùng khoá (lock) để tránh ghi chồng giữa các worker — không
  đợi hết batch mới ghi.
- **FR-006**: Dòng ghi MUST có dạng `{"id": <id câu hỏi>, "type": ..., "answer": ...}` hoặc
  `{"id": ..., "type": "unanswerable", "reason": ...}` — khớp đúng format mà `_load_submission`
  của `003-eval-harness` đọc được (đã đọc source, không đoán).
- **FR-007**: Nếu `answer_fn` raise exception HOẶC trả về giá trị không đúng hợp đồng (xem Edge
  Case tương ứng), `run_batch` MUST ghi dòng `{"type": "unanswerable", "reason": "lỗi xử lý:
  <mô tả>"}` cho câu đó và MUST tiếp tục xử lý các câu khác — KHÔNG dừng toàn bộ batch.
- **FR-008**: `run_batch` MUST chuẩn hoá đáp án trước khi ghi:
  (a) `type == "percent"` và `answer` là số (không phải `bool`) → `round(answer, 2)`.
  (b) `type == "table"` và `answer` là `dict` → map các alias key cố định (`"cols"` → `"columns"`,
  `"data"`/`"records"` → `"rows"`) sang đúng tên chuẩn nếu khớp alias; giữ nguyên nếu không khớp
  danh sách alias (không tự suy đoán ngoài danh sách đã định nghĩa).
  Các `type` khác (number/date/boolean/string/list/unanswerable) KHÔNG bị biến đổi — pass-through
  nguyên văn từ `answer_fn`.
- **FR-009**: `run_batch` MUST hỗ trợ tham số `limit`: nếu truyền, chỉ xử lý N câu đầu tiên trong
  phần CHƯA resume-skip.
- **FR-010**: Hệ thống MUST cung cấp CLI (`cli.py`) với tham số `--questions`, `--dataset-dir`,
  `--out`, `--concurrency` (default `1`), `--limit` (optional) — gọi `run_batch` với
  `answer_question` thật của `004-reasoning-agent`.
- **FR-011**: `run_batch` MUST raise lỗi rõ ràng ngay từ đầu (trước khi xử lý bất kỳ câu nào) nếu
  phát hiện `id` trùng lặp trong `questions_path`, hoặc `concurrency < 1`.
- **FR-012**: `run_batch` MUST trả về `BatchSummary` gồm ít nhất: tổng số câu, số câu resume-skip,
  số câu xử lý trong lượt chạy này, số câu lỗi (ghi `unanswerable` do exception/hợp đồng sai),
  thời gian chạy (giây).

### Key Entities

- **QuestionRow**: `{"id", "business_id", "question", "as_of_date"}` — đọc từ `questions.jsonl`
  của 1 `dataset_dir`.
- **SubmissionRow**: `{"id", "type", "answer"}` hoặc `{"id", "type": "unanswerable", "reason"}` —
  ghi ra `out_path`, 1 dòng/câu hỏi.
- **BatchSummary**: thống kê 1 lượt chạy — xem FR-012.

## 🎯 Success Criteria (mandatory)

- **SC-001**: Chạy CLI trên toàn bộ `train/questions.jsonl` (3000 câu) với `answer_fn` giả tốc độ
  cao (không gọi LLM thật) → đúng 3000 dòng submission, không trùng/thiếu `id`, `score_submission`
  (003) đọc được không lỗi format.
- **SC-002**: Resume thật — dừng batch giữa chừng (~50%) rồi chạy lại đúng lệnh → không gọi lại
  `answer_fn` cho câu đã xong, cuối cùng đủ số dòng mong đợi.
- **SC-003**: `--concurrency 4` với `answer_fn` giả chạy chậm (sleep ngắn mô phỏng gọi LLM) cho
  tổng thời gian chạy NGẮN HƠN RÕ RỆT so với `--concurrency 1` trên cùng tập câu hỏi — chứng minh
  song song thật, không phải giả song song.
- **SC-004**: Chạy 1 lần thật (không giả) trên mẫu nhỏ thật (~10 câu) từ `train/` qua
  `answer_question` thật của `004` → ra `submission.jsonl` hợp lệ, `score_submission` chạy được,
  không crash (test tích hợp chậm, `skipif` theo biến môi trường — giống
  `test_baseline_golden.py` của 004).

## 💡 Assumptions

- `answer_question` (004) là nguồn sự thật duy nhất cho NỘI DUNG đáp án — 005 không tự đoán/sửa
  giá trị, chỉ làm tròn `percent` + chuẩn hoá key `table` theo alias cố định (FR-008), không suy
  luận lại nội dung.
- 1 `dataset_dir` cố định cho mỗi lượt chạy (không trộn `train/` + `public_test/` trong 1 lệnh) —
  khớp với cách `answer_question` nhận `dataset_dir`.
- `answer_question` an toàn khi gọi đồng thời từ nhiều thread: mỗi lời gọi tự mở 1 connection
  DuckDB read-only riêng + 1 lời gọi HTTP riêng tới LLM server, không có state toàn cục chia sẻ
  (đã xác nhận qua đọc `src/reasoning_agent/agent.py`).
- `id` trùng lặp trong `questions.jsonl` thực tế KHÔNG xảy ra với dữ liệu do BTC cấp — guard ở
  FR-011 chỉ là an toàn khi dữ liệu lỗi, không phải case mong đợi.
- Ép deadline tổng (6h cho `private_test`) và xử lý bị kill ở tầng container là phạm vi của
  `006-docker-packaging`, KHÔNG phải 005 (005 chỉ cung cấp `--concurrency` làm chỗ 006 tận dụng
  phần cứng mạnh hơn, và cơ chế resume làm chỗ 006 dựa vào nếu cần chạy lại sau khi bị kill).
