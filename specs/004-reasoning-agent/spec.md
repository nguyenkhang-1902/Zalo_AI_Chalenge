# Feature Specification: Reasoning Agent

**Feature Branch**: `004-reasoning-agent` | **Created**: 2026-10-31 | **Status**: 🚧 Draft

## User Scenarios & Testing (mandatory)

### User Story 1 - Trả lời đúng 1 câu hỏi kinh doanh tự nhiên cho 1 business (Priority: P1)

Với 1 `business_id` đã có DuckDB + `schema.json` (sinh bởi `001-data-loader`), 1 câu hỏi tiếng
Việt tự nhiên về số liệu/thời gian kinh doanh, và 1 `as_of_date`, hệ thống phải tự suy luận (đọc
schema + `rulebook.md` của chính bộ dữ liệu, giải nghĩa thời gian tương đối qua `date_resolver`,
query DuckDB) và trả về đúng loại + đúng nội dung đáp án.

**Why this priority**: Đây là lõi suy luận của toàn pipeline — không có sub-project này, không
câu hỏi nào trả lời được, 005/006 không có gì để đóng gói.

**Independent Test**: Gọi `answer_question(...)` trên 1 mẫu câu hỏi thật từ
`train/questions.jsonl`, đưa thẳng kết quả `{"type", "answer"}` (gắn thêm `id` từ câu hỏi) qua
`score_submission` của `003-eval-harness` để có điểm số ngay — không cần `005-answer-formatter`
hay `006-docker-packaging` tồn tại. Điểm số này là ước lượng thô (chưa qua format-chuẩn-hoá của
005) nhưng đủ để biết pipeline suy luận có đúng hướng hay không.

**Acceptance Scenarios**:

1. **Given** câu hỏi có cách nói thời gian tương đối đã định nghĩa ở `rulebook.md` §2 (vd "tháng
   này", "7 ngày gần nhất"), **When** agent xử lý, **Then** agent gọi đúng 1 trong 12 tool
   `date_resolver` khớp với cách nói đó (không tự viết logic tính ngày riêng).
2. **Given** câu hỏi cần lọc số liệu phát sinh thực tế theo 1 khoảng ngày còn đang diễn ra tính
   đến `as_of_date` (vd "tháng này" khi tháng chưa hết), **When** agent viết SQL lọc, **Then**
   agent dùng `query_end` (đã cắt tại `as_of_date`) của tool trả về, không dùng `end` (kỳ đầy đủ).
3. **Given** câu hỏi dạng "đến hết ngày X" (kỳ cố định quá khứ, X là ngày cụ thể đọc thẳng từ câu
   hỏi), **When** agent xử lý, **Then** agent KHÔNG gọi tool `date_resolver` nào (không có cách
   nói tương đối cần giải nghĩa) — dùng thẳng ngày X đọc được.
4. **Given** agent viết SQL sai cú pháp/sai tên cột, **When** `run_sql` chạy, **Then** tool trả về
   nguyên văn lỗi DuckDB (không raise exception làm sập loop), agent còn ngân sách bước để tự sửa.
5. **Given** agent dùng hết 6 bước gọi tool hoặc vượt 45s cho 1 câu hỏi mà chưa ra đáp án hợp lệ,
   **When** ngân sách hết, **Then** hệ thống TỰ ĐỘNG trả `{"type": "unanswerable", "reason":
   "hết ngân sách bước suy luận"}` — đây là guard vận hành (hết giờ), KHÔNG phải agent tự quyết
   định nội dung không trả lời được.
6. **Given** câu hỏi mà agent (không phải hệ thống) tự đánh giá không đủ dữ liệu để trả lời,
   **When** agent kết luận, **Then** agent tự trả `{"type": "unanswerable", "reason": "..."}` —
   quyết định nội dung này hoàn toàn do agent, hệ thống không có rule cứng áp sẵn cho trường hợp
   nào MUST trả unanswerable (trừ guard vận hành ở Acceptance Scenario 5).
7. **Given** 2 business khác nhau có schema hoàn toàn khác nhau (tên bảng/cột khác), **When**
   agent xử lý câu hỏi của business bất kỳ, **Then** không có đoạn code nào rẽ nhánh theo
   `business_id` cụ thể — toàn bộ xử lý tổng quát theo schema đọc được lúc runtime.
8. **Given** đổi model LLM phục vụ (Qwen2.5-7B-Instruct dev ↔ Qwen2.5-14B-Instruct lúc đóng
   Docker), **When** đổi 1 biến config/env var, **Then** không cần sửa code nguồn nào của
   `004-reasoning-agent`.

### Edge Cases

- ⚠️ Model gọi tool với tên/tham số không hợp lệ (hallucinate tool không tồn tại, thiếu tham số
  bắt buộc) → trả lỗi rõ ràng cho model (không raise), tính vào ngân sách bước.
- ⚠️ `run_sql` nhận câu lệnh KHÔNG phải `SELECT` (vd `INSERT`/`DROP`) → connection chỉ mở
  read-only, DuckDB tự raise lỗi quyền, tool trả lỗi đó cho model như lỗi SQL thường — không có
  logic chặn riêng (không cần, vì query chạy trên dữ liệu của chính pipeline, không có kẻ tấn
  công ngoài).
- ⚠️ `rulebook.md`/`calendar.csv` của bộ dữ liệu đang chạy thiếu hoặc lỗi đọc → lỗi phải RAISE rõ
  ràng ngay lúc khởi tạo agent cho bộ dữ liệu đó (lỗi hạ tầng, không phải lỗi 1 câu hỏi, không
  nên âm thầm tiếp tục với rulebook rỗng).
- ⚠️ Câu hỏi không thuộc `business_id` nào có trong `/data` (business mới chưa từng thấy ở
  `train`/`public_test`) → agent vẫn phải hoạt động được chỉ dựa vào schema/README đọc runtime,
  không giả định cấu trúc trước (giống Edge Case tương ứng của `001-data-loader`).
- ⚠️ 1 business có RẤT nhiều table (vd 24 file như `dev_005`) → prompt mặc định (chỉ tên
  bảng/cột/dtype, không kèm sample_values/README đầy đủ) phải đủ gọn để nằm trong context window
  của model mục tiêu; `get_table_detail`/`get_readme` là lối thoát khi cần chi tiết hơn.

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: Hệ thống MUST cung cấp `answer_question(question: str, business_id: str,
  as_of_date: date, dataset_dir: Path) -> dict`, trả về `{"type": str, "answer": Any}` với
  `type` là 1 trong 8 kiểu của `rulebook.md` §9 (number/percent/date/boolean/string/list/table/
  unanswerable).
- **FR-002**: System prompt mặc định MUST gồm: tên bảng + tên cột + dtype của mọi table thuộc
  `business_id` (đọc từ `schema.json` do `001` sinh), và nguyên văn `rulebook.md` của chính
  `dataset_dir` đang chạy, đọc tại runtime — KHÔNG bake cứng bản nào vào code/prompt tĩnh
  (checklist C4).
- **FR-003**: Hệ thống MUST cung cấp các tool sau cho model gọi qua function-calling trong vòng
  ReAct:
  - `run_sql(query: str)` — chạy trên connection DuckDB READ-ONLY của `business_id`, trả rows
    hoặc lỗi DuckDB nguyên văn (không raise).
  - 12 tool 1:1 với các hàm công khai của `date_resolver` dùng để giải nghĩa thời gian tương đối:
    `today`, `n_days_ago`, `this_week`, `last_week`, `year_to_date`, `month_of`, `this_month`,
    `comparable_last_month`, `month_or_quarter_without_year`, `shift_session`, `tet_period`,
    `comparable_before_tet`. (`CalendarIndex`/`load_calendar` KHÔNG phải tool — dùng 1 lần lúc
    khởi tạo agent cho 1 `dataset_dir` để nạp `calendar.csv` thành index truyền vào 2 tool liên
    quan Tết.)
  - `get_readme()` / `get_table_detail(table_name: str)` — trả nguyên văn README và chi tiết đầy
    đủ 1 table (cột + sample_values) khi model cần hơn mức system prompt mặc định đã cho.
- **FR-004**: Mọi tool trong 12 tool `date_resolver` ở FR-003 MUST trả về cả `start`, `end`
  (kỳ đầy đủ, nguyên bản của `date_resolver`), và `query_end = min(end, as_of_date)`. System
  prompt MUST hướng dẫn model dùng `query_end` khi lọc số liệu phát sinh thực tế, dùng `end` khi
  câu hỏi tự nó đã là 1 kỳ cố định trong quá khứ (checklist C6).
- **FR-005**: Vòng ReAct MUST giới hạn tối đa 6 lượt gọi tool và tổng 45 giây mỗi câu hỏi. Vượt
  1 trong 2 ngưỡng mà chưa có đáp án hợp lệ MUST trả về `{"type": "unanswerable", "reason": "hết
  ngân sách bước suy luận"}` thay vì raise lỗi hoặc treo.
- **FR-006**: Quyết định NỘI DUNG có nên trả `unanswerable` hay không (ngoài guard vận hành ở
  FR-005) MUST hoàn toàn do model tự suy luận — hệ thống MUST NOT áp bất kỳ rule cứng định sẵn
  nào cho việc này (vd không hard-code "thiếu cột X thì luôn unanswerable").
- **FR-007**: Tên/endpoint model LLM MUST đọc từ config/env var, MUST NOT hard-code ở bất kỳ đâu
  trong source — đổi từ Qwen2.5-7B-Instruct (dev) sang Qwen2.5-14B-Instruct (Docker nộp thật, C2)
  chỉ qua đổi giá trị config.
- **FR-008**: Lúc gọi model MUST dùng temperature thấp/0 + seed cố định (Điều 9 — giảm phần ngẫu
  nhiên để đạt `|PA(nộp) − PA(re-run)| ≤ 0.03`).
- **FR-009**: Hệ thống MUST NOT chứa bất kỳ logic rẽ nhánh theo `business_id`/`question_id` cụ
  thể (Điều 10, giống FR-009 của `001-data-loader`).
- **FR-010**: Giá trị `answer` trả về từ `answer_question` KHÔNG BẮT BUỘC đúng tuyệt đối format
  cuối của `rulebook.md` §9 (vd `percent` chưa tròn đúng 2 chữ số, `table` chưa chắc đúng key
  `"columns"`/`"rows"`) — chỉ cần đúng NỘI DUNG + đúng `type`. Chuẩn hoá format cuối thuộc phạm vi
  `005-answer-formatter`.

### Key Entities

- **ReasoningRequest**: `question` (text câu hỏi), `business_id`, `as_of_date`, `dataset_dir` —
  input của `answer_question`.
- **ReasoningResult**: `{"type": str, "answer": Any}` — output của `answer_question`, nội dung
  đúng, format chưa chắc chuẩn (xem FR-010).
- **ToolCall / ToolResult**: cặp yêu cầu-gọi-tool và kết quả trả về trong vòng ReAct, không lộ ra
  ngoài `answer_question` (nội bộ `react_loop.py`).

## 🎯 Success Criteria (mandatory)

- **SC-001**: Chạy `answer_question` trên 100 câu hỏi mẫu từ `train/questions.jsonl` (rải đều cả
  8 answer type) — không câu nào crash hoặc vượt 45s mà không rơi về `unanswerable` theo FR-005.
- **SC-002**: Baseline accuracy đo bằng `score_submission` (003) trên mẫu 100 câu ở SC-001 PHẢI
  lớn hơn 0% (chứng minh cơ chế suy luận end-to-end hoạt động đúng, không phải lỗi hệ thống) —
  KHÔNG đặt ngưỡng % cụ thể cho version đầu, vì đây là mốc để các vòng cải thiện prompt/tool sau
  so sánh, không phải tiêu chí nghiệm thu cuối.
- **SC-003**: Đổi model LLM phục vụ (7B ↔ 14B, hoặc endpoint khác) chỉ qua đúng 1 biến
  config/env var — `grep` source không còn tên model nào hard-code.
- **SC-004**: `grep` source không có điều kiện rẽ nhánh theo `business_id`/`question_id` cụ thể
  nào (SC tương ứng FR-009).
- **SC-005**: Thời gian xử lý trung bình/câu hỏi (đo trên mẫu SC-001, gồm thời gian gọi model)
  nằm trong ngân sách suy ra từ 6h tổng / số câu hỏi `private_test` dự kiến (dùng `public_test`
  1000 câu làm cận trên tạm tính nếu chưa biết số thật của `private_test`).

## 💡 Assumptions

- `rulebook.md` §2 định nghĩa đủ chính xác mọi cách nói thời gian tương đối để model map đúng
  sang 1 trong 12 tool `date_resolver` — không cần 1 bộ phân loại NLP riêng (đã kiểm chứng gián
  tiếp qua test case thật của `002-date-calendar-resolver`).
- Qwen2.5-Instruct (7B/14B) hỗ trợ function-calling đủ tốt cho palette ~15 tool (`run_sql` + 12
  date tool + `get_readme` + `get_table_detail`) mà không cần fine-tune riêng.
- Connection DuckDB READ-ONLY là đủ cách ly cho SQL do model tự sinh — không cần sandbox Python
  đầy đủ, vì không có kẻ tấn công ngoài (model chỉ tự đọc dữ liệu của chính pipeline).
- `005-answer-formatter` sẽ đảm nhận: tròn `percent` đúng 2 chữ số, chuẩn hoá key `table`
  (`"columns"`/`"rows"`), giữ đúng thứ tự `list`, và ghép `id` + ghi `submission.jsonl` cuối cùng
  — `004` không cần làm những việc này.
- Số câu hỏi thật của `private_test` chưa biết tại thời điểm viết spec này (công bố 20/11) — SC-005
  dùng `public_test` (1000 câu) làm cận trên tạm tính, sẽ cập nhật lại khi `private_test` công bố.
