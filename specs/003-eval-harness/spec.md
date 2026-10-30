# Feature Specification: Eval Harness

**Feature Branch**: `003-eval-harness` | **Created**: 2026-10-30 | **Status**: 🚧 Draft

## User Scenarios & Testing (mandatory)

### User Story 1 - Chấm điểm 1 submission theo đúng rulebook §9 (Priority: P1)

Trong lúc phát triển `004-reasoning-agent`/`005-answer-formatter`, cần biết NGAY pipeline đang
đúng bao nhiêu % trên `train/` (bộ duy nhất có ground truth) mà không phải nộp lên portal. Eval
harness đọc `questions.jsonl` + `answers.jsonl` (ground truth) + `submission.jsonl` (đáp án pipeline
sinh ra), áp đúng công thức chấm điểm + format của `rulebook.md` §9, trả về báo cáo tổng + chi tiết
theo answer type và theo business, để biết ngay đang yếu ở đâu.

**Why this priority**: Không có cách đo được chất lượng pipeline trước khi nộp thật — không biết
004/005 đang đúng hướng hay sai lệch ở đâu, lãng phí lượt nộp (tối đa 5 lần/ngày, 2 lần nộp Docker).

**Independent Test**: Gọi `score_submission(...)` với 1 `submission.jsonl` tự dựng (copy từ
`train/answers.jsonl`, đổi format đúng kiểu submission) → kỳ vọng accuracy 100%, không cần
`004-reasoning-agent` tồn tại.

**Acceptance Scenarios**:

1. **Given** `submission.jsonl` là bản sao ĐÚNG của `train/answers.jsonl` (đổi format cho đúng
   `submission.jsonl`), **When** chấm điểm, **Then** `total_score == total_questions`,
   `accuracy == 1.0`, không có câu nào sai.
2. **Given** `submission.jsonl` cố ý sửa sai giá trị của N câu (N biết trước), **When** chấm điểm,
   **Then** điểm giảm đúng `2*N` so với kịch bản hoàn hảo (mỗi câu sai: mất 1 điểm đúng + thêm 1
   điểm trừ = lệch 2 so với đúng).
3. **Given** `submission.jsonl` thiếu dòng cho 1 số `id` (không trả lời), **When** chấm điểm,
   **Then** các `id` đó tính 0 điểm (không phải -1), xuất hiện trong `abstained`.
4. **Given** `submission.jsonl` có dòng `{"type": "abstain"}` cho 1 `id`, **When** chấm điểm,
   **Then** tính 0 điểm giống như thiếu dòng.
5. **Given** câu hỏi type `string` mà ground truth có `alias` (vd mã sản phẩm `"SP0001"`),
   **When** submission trả đúng mã đó (khác chuỗi tên nhưng đúng alias), **Then** vẫn tính đúng
   (+1).
6. **Given** câu hỏi type `table` mà submission trả đúng dữ liệu nhưng **thứ tự dòng khác** ground
   truth, **When** chấm điểm, **Then** vẫn tính đúng (+1) — rulebook §9 nói rõ thứ tự dòng không
   ảnh hưởng.
7. **Given** câu hỏi type `list` mà submission đúng giá trị nhưng **sai thứ tự phần tử**,
   **When** chấm điểm, **Then** tính sai (-1) — rulebook §9 nói rõ list phải đúng thứ tự.
8. **Given** 1 dòng trong `submission.jsonl` là JSON hỏng (không parse được), **When** chấm điểm
   cả file, **Then** các dòng khác vẫn được chấm bình thường, dòng hỏng tính 0 điểm, không crash.

### Edge Cases

- ⚠️ `id` trùng lặp trong `submission.jsonl` → MUST raise `ValueError` ngay (lỗi sinh ra từ
  004/005, cần biết sớm, không âm thầm lấy dòng đầu/cuối).
- ⚠️ `id` lạ trong `submission.jsonl` không có trong `answers.jsonl` → bỏ qua, không ảnh hưởng
  điểm, đếm vào `extra_ids_ignored` để cảnh báo (có thể là bug sinh sai id).
- ⚠️ `answers.jsonl` thiếu entry cho 1 `id` có trong `questions.jsonl` → MUST raise `ValueError`
  (lỗi dữ liệu ground truth, khác hẳn case submission thiếu id).
- ⚠️ Type dự đoán khác type ground truth (vd đoán `string` nhưng đúng `number`) → sai format → -1,
  KHÔNG raise (đây là kết quả chấm điểm hợp lệ, không phải lỗi hệ thống).
- ⚠️ Giá trị `number`/`percent` lệch do sai số dấu phẩy động (vd `12.399999999` vs `12.4`) → vẫn
  tính đúng (dùng epsilon nhỏ, không so bằng tuyệt đối).

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: Hệ thống MUST cung cấp hàm `score_submission(questions_path, answers_path,
  submission_path) -> EvalReport` đọc cả 3 file JSONL và tính điểm.
- **FR-002**: Hệ thống MUST áp đúng công thức rulebook §9: đúng `+1`, sai `−1`, bỏ trống (thiếu
  dòng hoặc `{"type": "abstain"}`) `0`.
- **FR-003**: Hệ thống MUST kiểm tra ĐÚNG FORMAT trước khi so giá trị — sai format (type khác,
  cấu trúc JSON không đúng bảng §9) tính là sai (-1), không raise exception.
- **FR-004**: Hệ thống MUST so khớp `number`/`percent` bằng epsilon nhỏ (chỉ bỏ qua sai số dấu
  phẩy động), không so bằng tuyệt đối kiểu `==`.
- **FR-005**: Hệ thống MUST so khớp `date`/`boolean` bằng so sánh giá trị trực tiếp (ground truth
  đã đúng granularity theo câu hỏi).
- **FR-006**: Hệ thống MUST so khớp `string` không phân biệt hoa/thường, khoảng trắng, dấu câu,
  nhưng GIỮ NGUYÊN yêu cầu đúng dấu tiếng Việt; MUST nhận cả `answer` và mọi phần tử trong `alias`.
- **FR-007**: Hệ thống MUST so khớp `list` theo ĐÚNG VỊ TRÍ — phần tử `i` đúng nếu khớp `answer[i]`
  hoặc BẤT KỲ phần tử nào trong `alias[i]` (`alias[i]` là 1 list mã thay thế cho vị trí đó, không
  phải 1 string đơn — đúng cấu trúc thật trong `answers.jsonl`, vd `"alias": [["SP0003"],
  ["SP0017"]]`); áp quy tắc theo type của phần tử (string dùng FR-006, number dùng FR-004); toàn
  bộ list chỉ đúng khi mọi phần tử đúng.
- **FR-008**: Hệ thống MUST so khớp `table`: so cột theo TÊN nếu toàn bộ tên khớp, ngược lại theo
  VỊ TRÍ; so dòng KHÔNG phân biệt thứ tự — match dòng dự đoán với dòng ground truth qua cột đầu
  (tên đối tượng, áp alias), rồi so các cột số đo còn lại theo FR-004.
- **FR-009**: Hệ thống MUST coi `unanswerable` là đúng chỉ cần `type == "unanswerable"`, không
  chấm nội dung field `reason`.
- **FR-010**: Hệ thống MUST trả về `EvalReport` gồm: tổng điểm, số câu đúng/sai/bỏ trống,
  accuracy, breakdown theo answer type, breakdown theo `business_id` (lấy từ `questions.jsonl`).
- **FR-011**: Hệ thống MUST xử lý dòng JSON hỏng trong `submission.jsonl` bằng cách tính 0 điểm
  cho dòng đó (không crash cả file), đếm vào `malformed_count`.
- **FR-012**: Hệ thống MUST raise `ValueError` khi `submission.jsonl` có `id` trùng lặp.
- **FR-013**: Hệ thống MUST raise `ValueError` khi `answers.jsonl` thiếu entry cho 1 `id` có
  trong `questions.jsonl`.
- **FR-014**: Hệ thống MUST cung cấp 1 CLI mỏng (`python -m eval_harness.cli --questions ...
  --answers ... --submission ...`) in ra report dễ đọc, dùng lại thẳng `score_submission`.
- **FR-015**: Hệ thống MUST NOT chứa logic rẽ nhánh theo `business_id`/`question_id` cụ thể nào
  (rule 4 cuộc thi) — chỉ dùng trong test/golden test.
- **FR-016** (phát hiện lúc final review, đọc lại rulebook §7): Hệ thống MUST tính 0 điểm (bỏ
  trống, không raise, không chấm theo type) cho MỌI dòng `submission.jsonl` có field `reason`
  mà giá trị KHÔNG phải chuỗi (`string`) — đúng nguyên văn rulebook §7: *"dòng có `reason` không
  phải chuỗi không đọc được và tính như bỏ trống"*. Áp dụng cho mọi answer type, không riêng
  `unanswerable` (vd 1 dòng type `number` đúng giá trị nhưng có `"reason": 123` vẫn tính 0, không
  phải +1).

### Key Entities

- **EvalReport**: tổng điểm, số đúng/sai/bỏ trống, accuracy, breakdown theo type, breakdown theo
  business, số dòng hỏng, số id lạ bị bỏ qua.
- **TypeBreakdown**: số đúng/sai/bỏ trống/tổng/accuracy — dùng lại cho cả breakdown theo type và
  theo business.

## 🎯 Success Criteria (mandatory)

- **SC-001**: Chấm 1 submission "hoàn hảo" (copy từ `train/answers.jsonl` thật) trên toàn bộ 3000
  câu của `train/` → accuracy đúng 100%, chạy xong trong vài giây (không phải mối lo hiệu năng ở
  sub-project này — dữ liệu chỉ 3000 dòng JSONL).
- **SC-002**: Mọi quy tắc so khớp (FR-004 → FR-009) có test đối chiếu trực tiếp với ví dụ thật
  trong `train/answers.jsonl` (không bịa dữ liệu) cho ít nhất 1 trường hợp mỗi type.
- **SC-003**: Không có logic rẽ nhánh theo `business_id`/`question_id` cụ thể trong module.

## 💡 Assumptions

- Chỉ `train/` có `answers.jsonl` (ground truth) — `public_test/`/`private_test` không có, vì đó
  là nơi BTC tự chấm. Harness này CHỈ dùng trong dev, không chạy trong Docker nộp bài (không cần
  đưa vào `006-docker-packaging`).
- Metric "PA" (reproducibility ΔPA≤0.03) nhắc trong luật BTC không được định nghĩa chi tiết trong
  `rulebook.md` — giả định đơn giản nhất: PA = accuracy (tỉ lệ câu đúng/tổng) hoặc điểm chuẩn hoá
  tương đương; không cần khớp tuyệt đối công thức BTC dùng nội bộ, vì harness này chỉ phục vụ DEV,
  không phải công cụ chấm điểm chính thức nộp lên portal.
- `question.jsonl`/`answers.jsonl` dùng chung `id` làm khoá liên kết; `business_id` chỉ có trong
  `questions.jsonl`.
- Hiệu năng không phải ràng buộc ở sub-project này (JSONL text nhỏ, không phải Excel/DB như 001).
