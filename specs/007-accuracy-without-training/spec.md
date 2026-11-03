# Feature Specification: Accuracy Without Training

**Feature Branch**: `007-accuracy-without-training` | **Created**: 2026-11-03 | **Status**: 🚧 Draft

> Bối cảnh: checklist C7 (baseline `004` ~10% trên model 7B/GPU 6GB) + C8 (Khang chọn hướng (c),
> 2026-11-03; không có GPU thuê, không có API teacher → fine-tune hoãn). Spec này là hướng (a) mở
> rộng: nâng điểm PA của pipeline hiện có mà KHÔNG train/fine-tune model nào.

## Vì sao điểm số, không chỉ accuracy

`PA = 1/N · Σ sᵢ` với đúng `+1`, abstain `0`, sai `−1`. Pipeline trả lời mọi câu với precision `p`
có kỳ vọng `2p − 1` mỗi câu → **âm khi p < 50%**. Baseline hiện tại (~10%) trả lời hết thì điểm
âm; chỉ trả lời khi đủ tin cậy thì điểm tối thiểu là 0. Vì vậy mục tiêu chính là **PA**, không
phải accuracy thô.

Phân bố `train/answers.jsonl` (3000 câu): number 1884 (62.8%), percent 578 (19.3%), list 193,
date 145, string 88, unanswerable 70, boolean 23, table 19. → ~82% câu là number/percent, tức
phần lớn câu là **tổng hợp có khoảng ngày + điều kiện lọc** — đây là chỗ đáng tối ưu nhất.

## User Scenarios & Testing (mandatory)

### User Story 1 - Abstain khi không đủ tin cậy (Priority: P1)

Pipeline chỉ trả đáp án khi đủ tin cậy, ngược lại trả `abstain` (không dòng đáp án / theo format
BTC cho phép), để PA không bị kéo xuống bởi câu sai.

**Why this priority**: Rẻ nhất, không đụng model, và biến điểm âm thành ≥ 0 ngay cả khi accuracy
thấp. Là nền để mọi cải tiến sau đo được trên cùng thang điểm PA.

**Independent Test**: Chạy bộ dev (xem SC-001) với và không có cổng tin cậy, chấm bằng
`score_submission` (003); so PA hai cấu hình.

**Acceptance Scenarios**:

1. **Given** N lần chạy độc lập (temperature/seed khác nhau có kiểm soát) cho cùng 1 câu hỏi cho
   ra đáp án không đồng thuận (dưới ngưỡng), **When** cổng tin cậy quyết định, **Then** hệ thống
   abstain thay vì trả đáp án phổ biến nhất.
2. **Given** các lần chạy đồng thuận ≥ ngưỡng, **Then** trả đáp án đồng thuận.
3. **Given** kết quả SQL rỗng/NULL/âm bất hợp lý cho kiểu câu hỏi số tiền, **When** agent chuẩn bị
   trả đáp án, **Then** coi là tín hiệu tin cậy thấp (hạ điểm tin cậy), không tự đổi sang
   `unanswerable` (FR-006 của 004 vẫn do model quyết).
4. **Given** ngưỡng tin cậy, **Then** ngưỡng là hằng số trong `config.py`/env (Điều 4), chọn bằng
   đường cong PA theo ngưỡng trên bộ dev, KHÔNG chọn bằng `public_test`.

### User Story 2 - Semantic-layer tool cho truy vấn tổng hợp (Priority: P1)

Thay vì để model viết SQL tự do cho dạng phổ biến (tổng/đếm/trung bình/top-N/so sánh cùng kỳ theo
khoảng ngày + bộ lọc), cung cấp tool có tham số, tự sinh SQL đúng từ schema đọc lúc runtime.

**Why this priority**: 82% câu là number/percent. Lỗi 004 gặp (sai tên cột, sai khoảng ngày, sai
công thức tổng hợp) đến từ bậc tự do quá lớn của SQL tự do với model nhỏ.

**Independent Test**: Chạy bộ dev với/không semantic-layer, so PA và tỷ lệ câu hết ngân sách
(FR-005 của 004).

**Acceptance Scenarios**:

1. **Given** model gọi tool tổng hợp với `table`, cột giá trị, cột ngày, `start`/`end` (từ
   `date_resolver`), danh sách điều kiện lọc, **When** tool chạy, **Then** SQL sinh ra dùng đúng
   tên cột có dấu/ngoặc kép từ `schema.json` và trả giá trị + số dòng khớp.
2. **Given** tham số tham chiếu bảng/cột không tồn tại, **Then** tool trả lỗi liệt kê tên bảng/cột
   hợp lệ gần nhất (không raise), tính vào ngân sách bước.
3. **Given** câu hỏi dạng không phủ được bởi semantic-layer, **Then** `run_sql` tự do vẫn còn là
   lối thoát (không bỏ tool cũ).
4. **Given** 2 business khác schema, **Then** không có nhánh theo `business_id`/tên cột cụ thể;
   toàn bộ suy ra từ schema runtime (FR-009 của 004).

### User Story 3 - Few-shot lấy từ train (Priority: P2)

Chèn vào prompt vài ví dụ gần nhất lấy từ `train/` (câu hỏi giống → `type` + dạng đáp án; thêm
quỹ đạo tool-call đã được xác minh đúng bằng `answers.jsonl` nếu có).

**Why this priority**: Hợp lệ (chỉ dùng train, rule 8.9.1) và không cần train model, nhưng lợi
ích kỳ vọng thấp hơn US1/US2 vì `train/` chỉ có đáp án, không có SQL — ví dụ chỉ chuyển giao được
**mẫu câu → kiểu đáp án/cách dùng tool**, không chuyển giao SQL giữa business khác schema.

**Independent Test**: A/B trên bộ dev với pool few-shot loại trừ các câu thuộc chính bộ dev.

**Acceptance Scenarios**:

1. **Given** câu hỏi mới, **When** chọn ví dụ, **Then** ví dụ lấy từ `train/` và KHÔNG chứa câu
   hỏi/đáp án của chính bộ dev (chống rò rỉ khi đo).
2. **Given** bộ dữ liệu chạy là `public_test`/`private_test`, **Then** pool few-shot vẫn chỉ từ
   `train/`; không có dữ liệu test nào đi vào pool (rule 8.9.2).
3. **Given** số ví dụ k, **Then** k và tổng token ví dụ nằm trong config và trong ngân sách
   context của model mục tiêu.

### User Story 4 - Đo model 14B trước khi nộp (Priority: P2)

Chạy Qwen 14B dạng GGUF Q4 qua llama.cpp (OpenAI-compatible, chỉ đổi biến config, FR-007 của 004)
trên máy công ty, đo PA trên bộ dev rút gọn để biết 14B hơn 7B bao nhiêu và có đáng chọn không.

**Why this priority**: Không nộp một model chưa từng chạy. Máy dev không chạy 14B nhanh, nên chỉ
đo mẫu nhỏ; vẫn có giá trị quyết định chọn model cho 006.

**Independent Test**: Cùng bộ dev rút gọn, chạy 7B và 14B-Q4 với cùng cấu hình tin cậy, so PA.

**Acceptance Scenarios**:

1. **Given** biến config trỏ endpoint llama.cpp, **When** chạy, **Then** không sửa code nguồn.
2. **Given** thời gian/câu của 14B-Q4 trên máy dev chậm hơn máy BTC, **Then** báo cáo ghi rõ số
   đo là cận trên về thời gian, không ngoại suy accuracy sang kết luận thời gian.
3. **Given** license/ngày phát hành của model, **Then** README ghi đủ để thoả rule 8.2/8.9 (phát
   hành trước 26/10/2026, license mở, tính cả LoRA nếu có).

### Edge Cases

- ⚠️ Self-consistency nhân N chi phí token/thời gian: tổng thời gian trên private (~500 câu) phải
  còn trong ngân sách 6h với 2×RTX 5090 (SC-004).
- ⚠️ Chạy nhiều lần cho cùng câu hỏi phải tất định ở cấp pipeline (seed theo chỉ số lần chạy,
  không theo `question_id`) để re-run BTC lệch ≤ 0.03 (rule 8.8, 8.9.6); không dùng thứ tự batch
  không tất định.
- ⚠️ Đồng thuận kiểu số cần so theo quy tắc khớp của BTC (làm tròn 2 số thập phân với percent,
  so sánh chuỗi đã chuẩn hoá) — tái dùng `eval_harness/matchers.py`, không viết lại.
- ⚠️ `abstain` phải đúng format BTC chấp nhận ("không dòng đáp án" hoặc `abstain` theo slide);
  đối chiếu với `rulebook.md` §9 và Docker guideline khi BTC công bố — chưa chốt thì mặc định
  bỏ dòng khỏi `submission.jsonl` (điểm 0 đã ghi ở slide chấm).
- ⚠️ Few-shot lấy từ `train/` có thể làm model bám mẫu câu của train → đo trên bộ dev loại trừ để
  tránh ảo tưởng cải thiện.

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: Hệ thống MUST có cổng tin cậy cho mỗi câu hỏi: trả đáp án hoặc `abstain`, quyết định
  từ độ đồng thuận giữa N lần chạy và/hoặc kiểm tra kết quả SQL; N, ngưỡng, seed nền đọc từ
  config/env (Điều 4).
- **FR-002**: Ngưỡng tin cậy MUST được chọn bằng đường cong PA trên bộ dev (từ `train/`), lưu kèm
  log đo; MUST NOT dùng `public_test`/`private_test` để chọn ngưỡng.
- **FR-003**: Hệ thống MUST cung cấp semantic-layer tool tham số hoá (tổng/đếm/trung bình/min/max,
  top-N, nhóm theo, so sánh cùng kỳ) sinh SQL từ `schema.json` lúc runtime, giữ nguyên `run_sql`
  làm lối thoát.
- **FR-004**: Semantic-layer MUST NOT chứa tri thức ngành/doanh nghiệp bake cứng (định nghĩa
  doanh thu, trạng thái đơn loại trừ…); mọi định nghĩa nghiệp vụ đến từ `rulebook.md` runtime qua
  model chọn tham số (checklist C4, Điều 10).
- **FR-005**: Hệ thống MUST có bộ chọn few-shot chỉ lấy từ `train/`, loại trừ được tập câu hỏi
  đang đo; số ví dụ và token tối đa đọc từ config.
- **FR-006**: Hệ thống MUST chạy được với endpoint llama.cpp/Ollama/vLLM chỉ bằng đổi
  `REASONING_AGENT_MODEL`/`REASONING_AGENT_BASE_URL` (FR-007 của 004), không sửa code.
- **FR-007**: MUST có script đo PA cho từng cấu hình (baseline, +cổng tin cậy, +semantic-layer,
  +few-shot, 7B vs 14B-Q4) trên cùng bộ dev cố định (seed cố định), xuất bảng so sánh bằng
  `eval_harness`; lưu log từng lần đo (Điều 9).
- **FR-008**: MUST NOT có logic rẽ nhánh theo `business_id`/`question_id` hay tên cột cụ thể
  (Điều 10, FR-009 của 004). `grep` nguồn sạch.
- **FR-009**: MUST NOT dùng bất kỳ dữ liệu `public_test`/`private_test` cho few-shot, chọn ngưỡng,
  hay tinh chỉnh prompt (rule 8.9.2).
- **FR-010**: Mọi thay đổi MUST giữ tính tất định pipeline (seed cố định theo chỉ số lần chạy,
  temperature theo config) để re-run ≤ 0.03 ΔPA.

### Key Entities

- **ConfidenceGate**: nhận N kết quả (đáp án chuẩn hoá + tín hiệu SQL), trả `answer` hoặc
  `abstain` + điểm tin cậy.
- **SemanticTool**: tool tham số hoá sinh SQL từ schema runtime, trả giá trị + metadata (số dòng,
  khoảng ngày) cho vòng ReAct.
- **FewShotPool**: tập ví dụ từ `train/` + chỉ mục tìm ví dụ gần nhất, hỗ trợ loại trừ tập đo.
- **DevSet**: mẫu cố định có phân tầng theo `type` từ `train/` dùng cho mọi phép đo trong spec này.

## 🎯 Success Criteria (mandatory)

- **SC-001**: Bộ dev cố định: 200 câu rút từ `train/`, phân tầng theo `type`, seed ghi trong
  config; (đo 14B-Q4 trên tập con 50–100 câu của chính bộ dev này).
- **SC-002**: PA(+cổng tin cậy) **≥ 0** trên bộ dev (không âm), và ≥ PA(baseline). Số liệu cụ thể
  ghi vào checklist.
- **SC-003**: Mỗi đòn bẩy (US2, US3) báo cáo PA trước/sau trên cùng bộ dev; một đòn bẩy không
  tăng PA bị ghi nhận "không có lợi", không tự động giữ lại chỉ vì đã làm.
- **SC-004**: Thời gian xử lý/câu (gồm N lần chạy) nằm trong ngân sách 6h trên 2×RTX 5090 cho
  ~500 câu private (cận trên tạm tính theo 1000 câu của `public_test`); ghi rõ phương pháp
  ngoại suy từ máy dev.
- **SC-005**: `grep` nguồn sạch `business_id ==`/`question_id ==`/tên model hard-code.
- **SC-006**: Chạy lặp cùng cấu hình 2 lần trên bộ dev, `|ΔPA| ≤ 0.03`.

## 💡 Assumptions

- Điểm đồng thuận giữa N lần chạy tương quan với độ đúng đủ để cổng tin cậy có lợi (giả thuyết
  này chính là thứ US1 đo; nếu không tương quan, kết luận được ghi lại thay vì ép).
- Semantic-layer giảm lỗi cú pháp/khoảng ngày/tên cột, nhưng KHÔNG giải quyết lỗi chọn sai điều
  kiện lọc nghiệp vụ theo rulebook — phần này vẫn phụ thuộc năng lực model (14B hơn 7B).
- `train/` không có SQL/quỹ đạo gốc, chỉ có đáp án → few-shot chỉ truyền được mẫu câu và kiểu đáp
  án; quỹ đạo đã xác minh (nếu có) chỉ sinh ra từ chính lần chạy của pipeline này, lọc bằng
  `answers.jsonl` (không train, chỉ làm ví dụ prompt).
- Máy dev chỉ RTX 3050 6GB/32GB RAM → 14B-Q4 chỉ đo mẫu nhỏ; số thời gian trên máy BTC (2×RTX
  5090) sẽ nhanh hơn nhiều và chỉ biết chắc khi có Docker guideline + chạy thật (thuộc 006).
- Định dạng chính xác của `abstain` trong `submission.jsonl` chưa được BTC xác nhận bằng văn bản
  ngoài slide chấm điểm; chờ Docker guideline.
- Fine-tune/distill (hướng (b)) nằm ngoài phạm vi spec này; chỉ mở lại nếu có nguồn lực mới
  (checklist C8).
