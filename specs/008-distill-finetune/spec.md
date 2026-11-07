# Feature Specification: Distill → Fine-tune (verified SQL distillation)

**Feature Branch**: `008-distill-finetune` | **Created**: 2026-11-07 | **Status**: 🚧 Draft

> Bối cảnh: 007 kết lại "fine-tune/distill (hướng b) ngoài phạm vi; chỉ mở lại nếu có nguồn lực
> mới (C8)". Giờ đã có nguồn lực: **teacher LLM lớn qua cổng API free** (repo gateway của Khang:
> Groq/OpenRouter/Together — chỉ dùng lúc SINH data, KHÔNG nằm trong Docker nộp) + **GPU train
> free Kaggle (2×T4 16GB)**. Hợp lệ theo Q&A 9.1 (được distill từ LLM lớn/API ngoài để train
> model nhỏ, miễn inference offline ≤15B; data tự tạo gửi BTC verify). Spec này mở lại hướng (b).

## Chẩn đoán dẫn tới spec này (đo thật, 60 câu dev baseline)

| Loại lỗi | Số câu | % | Ý nghĩa |
|---|---|---|---|
| **wrong_VALUE** (đúng kiểu, sai số) | 25 | **42%** | ⭐ SQL/tính sai (sai cột, sai filter, sai khoảng ngày) |
| abstain_budget (hết giờ RTX 3050) | 14 | 23% | Ảo giác phần cứng — biến mất trên máy chấm 2×5090 |
| abstain_model ("không có dữ liệu") | 10 | 17% | Schema-linking fail — không map được bảng/cột |
| wrong_TYPE (date, list) | 4 | 7% | Trượt nguyên nhóm đáp án |
| ĐÚNG | 3 | 5% | |

Nút thắt thật = **model sinh SQL sai**, không phải format/tốc độ. 007 đã xác nhận cổng tin cậy/
semantic-tool/few-shot chỉ giảm lỗ, không tạo điểm dương vì **năng lực SQL của base model quá
yếu**. Hướng duy nhất nâng trần năng lực mà không vi phạm luật là **fine-tune student bằng dữ
liệu SQL đã verify đúng** — dùng chính `train/answers.jsonl` làm bộ lọc "ground truth".

## Lợi thế vàng & nguyên lý

`train/` có **3000 câu KÈM đáp án đúng** (`answers.jsonl`). Cho phép **verified distillation
(rejection sampling)**: teacher sinh trace SQL → chạy thật trên DuckDB → **chỉ giữ trace nào ra
đúng đáp án gold** → data train sạch, không cần người gán nhãn. Student học "câu hỏi tiếng Việt +
schema runtime → SQL đúng", đúng kỹ năng đang thiếu.

**Ranh giới hợp lệ (bất biến):** teacher chỉ xuất hiện ở bước sinh data (offline, máy dev/Kaggle,
KHÔNG vào Docker). Model nộp bài = student ≤15B chạy offline. Chỉ dùng `train/` (rule 8.9.2 —
tuyệt đối không `public_test`/`private_test`). Data tự tạo gửi BTC verify (rule 8.9.1/8.9.3).

## User Scenarios & Testing (mandatory)

### User Story 1 — Sinh trace SQL đã verify từ train (Priority: P1)

Teacher đọc (câu hỏi + `as_of_date` + schema runtime + README + rulebook của business đó) rồi
sinh trace theo **đúng format ReAct tool-calling của 004** (không phải SQL trần), chạy thật, lọc
bằng đáp án gold; giữ lại trace đúng làm mẫu SFT.

**Why this priority**: Đây là lõi — không có dataset verified thì không có gì để train. Dùng lại
được ngay cho cả hướng không-train (few-shot bank của 007 US3) lẫn hướng train (US2).

**Independent Test**: Chạy generator trên 1 batch nhỏ (vd 50 câu train) → đếm **yield** (% câu có
≥1 trace verified) + kiểm trace chạy lại ra đúng đáp án bằng `eval_harness/matchers.py`.

**Acceptance Scenarios**:

1. **Given** câu train + schema.json + rulebook của business, **When** teacher sinh trace và chạy,
   **Then** trace dùng đúng tool/format của `react_loop` (004), SQL dùng đúng tên cột có dấu từ
   `schema.json`, kết quả so khớp gold bằng `matchers.py` (tái dùng, không viết lại).
2. **Given** teacher sinh sai lần 1, **When** còn trong `max_attempts` (config), **Then**
   rejection-sample thêm lần (temperature > 0) rồi mới bỏ; câu không verify được sau `max_attempts`
   bị loại khỏi dataset (ghi log lý do), KHÔNG đưa trace sai vào train.
3. **Given** teacher endpoint là cổng API free có rate-limit, **Then** generator có retry/backoff +
   **cache theo `question_id`** để chạy lại không gọi lại câu đã xong (tiết kiệm quota, tất định).
4. **Given** đang sinh data, **Then** KHÔNG câu nào thuộc **DevSet** (bộ đo của 007/003) lọt vào
   dataset train (chống rò rỉ khi đo PA trước/sau).

### User Story 2 — QLoRA fine-tune student trên Kaggle free (Priority: P1)

Fine-tune model student ≤15B (mặc định **Qwen2.5-Coder-7B-Instruct** — giỏi SQL, QLoRA 4-bit vừa
1×T4) trên dataset verified của US1, sinh LoRA adapter. Student sau train phải **chạy được qua
endpoint OpenAI-compatible mà KHÔNG sửa code 004** (đổi `REASONING_AGENT_MODEL`/`BASE_URL`).

**Why this priority**: Đây là bước nâng trần năng lực. Ràng buộc free Kaggle là lý do chọn 7B
QLoRA (14B QLoRA chật trên T4 free — để sau nếu 7B chạm trần).

**Independent Test**: Train 1 epoch trên dataset nhỏ → load adapter → chạy `react_loop` trên 5 câu
dev, xác nhận model nói đúng format tool-calling và sinh được SQL (chưa cần đúng hết — US3 mới đo PA).

**Acceptance Scenarios**:

1. **Given** dataset SFT (format chat/tool của student), **When** chạy script train QLoRA trên T4,
   **Then** job xong trong giới hạn Kaggle (thời gian/VRAM ghi trong báo cáo), xuất LoRA adapter +
   config tái lập (seed, lr, epoch).
2. **Given** adapter đã train, **When** serve qua llama.cpp/vLLM OpenAI-compatible, **Then**
   `reasoning_agent` dùng được chỉ bằng đổi biến env (FR-007 của 004), không sửa `src/`.
3. **Given** base model, **Then** README solution khai báo: tên model, ngày phát hành (trước
   26/10/2026), license (OSI), LoRA tính vào tổng ≤15B (rule 8.2) — xác nhận cụ thể trước khi chốt.

### User Story 3 — Đo PA trước/sau trên phần cứng sạch (Priority: P1)

Đo PA của student **đã fine-tune** vs baseline trên **cùng DevSet cố định** (007 SC-001), bằng
`eval_harness` (003), trên môi trường **fit-VRAM không offload** (Kaggle T4) để loại nhiễu
abstain_budget của RTX 3050.

**Why this priority**: SDD Điều 2 — không báo "xong" nếu chưa có số PA thật. Phải chứng minh
fine-tune có lợi, nếu không thì ghi nhận "không có lợi" (không giữ chỉ vì đã train).

**Independent Test**: Chạy baseline vs fine-tuned trên DevSet ở cùng ngân sách thời gian + cùng
cổng tin cậy (007), so PA + accuracy thô + phân bố loại lỗi (wrong_VALUE giảm không).

**Acceptance Scenarios**:

1. **Given** cùng DevSet + cùng cấu hình tin cậy, **When** so baseline vs fine-tuned, **Then** báo
   cáo PA trước/sau + Δ, và so phân loại lỗi (kỳ vọng wrong_VALUE giảm).
2. **Given** đo trên Kaggle T4 (fit VRAM), **Then** ghi rõ đây là số sạch hơn RTX 3050; thời gian/
   câu chỉ là cận trên so với 2×5090 (không ngoại suy accuracy sang thời gian).
3. **Given** fine-tune không nâng PA, **Then** kết luận được ghi vào checklist C8 (âm/0 vẫn là dữ
   kiện), cân nhắc đổi student/thêm data thay vì ép giữ.

### User Story 4 — Bàn giao cho 006 + tuân thủ (Priority: P2)

Đóng gói model student (base + adapter, hoặc merged) vào đường vLLM của `006-docker-packaging`, và
chuẩn bị gói tuân thủ: data train + code train gửi BTC verify, khai báo model trong README.

**Why this priority**: 006 chưa làm; model fine-tune phải chạy được trong Docker offline thật thì
mới có điểm. Tách P2 vì phụ thuộc Docker guideline BTC (chưa công bố).

**Acceptance Scenarios**:

1. **Given** adapter + base, **When** 006 dựng Docker, **Then** student chạy offline qua vLLM
   (CUDA 12.9, 2×5090), không gọi mạng; tổng tham số inference ≤15B.
2. **Given** rule 8.9.3, **Then** đóng gói đủ cho BTC: code inference + **code train/distill + dữ
   liệu dùng để train** (dataset verified) + tài liệu để tái lập.
3. **Given** rule 8.9.1, **Then** dataset tự tạo được chuẩn bị sẵn để gửi `aichallenge@zalo.me`
   verify.

### Edge Cases

- ⚠️ **Format mismatch**: trace train PHẢI trùng format inference (ReAct tool-calling của 004), nếu
  không SFT dạy sai thứ. Generator render trace đúng schema message/tool của student.
- ⚠️ **Rò rỉ DevSet**: câu dùng đo PA tuyệt đối không nằm trong data train (loại theo id trước khi train).
- ⚠️ **Overfit schema train**: `private_test` có schema/ngành mới → fine-tune phải dạy **kỹ năng
  suy luận trên schema cho trong prompt**, không nhớ cứng schema train. Không bake `business_id`/tên
  cột; đa dạng hoá business trong data; dedupe trace trùng.
- ⚠️ **Rate-limit cổng API free**: sinh ~nghìn trace sẽ đụng quota → backoff + cache + chạy nhiều
  phiên; yield thấp thì ưu tiên loại câu number/percent (82% bộ đề) trước.
- ⚠️ **Tất định**: student sau train vẫn phải temp 0 + seed cố định để re-run BTC |ΔPA| ≤ 0.03 (8.8).
- ⚠️ **License/ngày phát hành student**: xác nhận trước khi chốt model (rule 8.2); nếu base không
  thoả, đổi sang base hợp lệ tương đương.
- ⚠️ **matchers khớp gold**: tái dùng `eval_harness/matchers.py` khi lọc trace (number tolerance,
  percent làm tròn, chuỗi chuẩn hoá) — không viết lại logic khớp.

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: Hệ thống MUST có generator sinh trace cho câu `train/`: input = câu hỏi + `as_of_date`
  + `schema.json` + README + rulebook runtime của business; output = trace theo format tool-calling
  của 004; teacher endpoint/model đọc từ config/env.
- **FR-002**: Generator MUST chạy SQL của trace thật trên DuckDB và chỉ GIỮ trace có kết quả khớp
  đáp án `train/answers.jsonl` qua `eval_harness/matchers.py`; trace sai bị loại, KHÔNG vào dataset.
- **FR-003**: Generator MUST rejection-sample tới `max_attempts` (config) với temperature>0, có
  retry/backoff cho rate-limit, và cache theo `question_id` để tất định + tiết kiệm quota.
- **FR-004**: Dataset SFT MUST loại trừ mọi câu thuộc DevSet đo PA (007 SC-001) và MUST NOT chứa
  bất kỳ dữ liệu `public_test`/`private_test` (rule 8.9.2).
- **FR-005**: MUST có script fine-tune QLoRA (student ≤15B, mặc định Qwen2.5-Coder-7B) chạy được
  trên Kaggle T4 free, xuất LoRA adapter + config tái lập (seed/lr/epoch/batch).
- **FR-006**: Student sau train MUST dùng được bởi `reasoning_agent` chỉ qua đổi
  `REASONING_AGENT_MODEL`/`REASONING_AGENT_BASE_URL` (FR-007 của 004), MUST NOT sửa `src/` lõi agent.
- **FR-007**: MUST có script đo PA baseline vs fine-tuned trên cùng DevSet (seed cố định) bằng
  `eval_harness`, xuất bảng PA + phân loại lỗi; lưu log từng lần (Điều 9).
- **FR-008**: MUST NOT có logic rẽ nhánh theo `business_id`/`question_id`/tên cột cụ thể trong
  generator lẫn data (Điều 10); `grep` nguồn + kiểm mẫu data sạch.
- **FR-009**: Tổng tham số model lúc inference (base + LoRA + mọi model phụ) MUST ≤ 15B; base MUST
  public trước 26/10/2026 + license hợp lệ; khai báo trong README (rule 8.2).
- **FR-010**: MUST giữ tất định pipeline inference sau train (temp 0, seed cố định) để re-run ≤0.03 ΔPA.
- **FR-011**: MUST đóng gói được **code train + dataset verified + tài liệu** để gửi BTC (rule 8.9.3);
  teacher (API ngoài) MUST NOT là dependency lúc inference/Docker.

### Key Entities

- **TeacherClient**: client OpenAI-compatible tới cổng API free (config base_url/model/key qua env),
  retry/backoff, đếm token/quota. Chỉ dùng lúc data-gen.
- **TraceGenerator**: ghép prompt (câu + schema + rulebook), gọi teacher, parse trace tool-calling,
  chạy SQL trên DuckDB, verify bằng matchers, cache, ghi dataset.
- **SFTDataset**: JSONL mẫu `{messages/tools → completion}` đúng format student; kèm metadata
  (`question_id`, business, type, số attempt) để audit/gửi BTC.
- **FineTuneJob**: script QLoRA (Unsloth/TRL) + config; output adapter + log train.
- **EvalRunner**: tái dùng `eval_harness` (003) đo PA trước/sau trên DevSet.

## 🎯 Success Criteria (mandatory)

- **SC-001**: Generator chạy được trên ≥1 batch train và đạt **yield verified > 0** (báo cáo yield
  theo `type`); trace giữ lại chạy lại ra đúng đáp án 100% (vì đã lọc bằng matchers).
- **SC-002**: PA(fine-tuned) trên DevSet **> PA(baseline)** ở cùng cấu hình/ngân sách; nếu không,
  ghi nhận "không có lợi" + lý do (SDD Điều 2, không giữ ép).
- **SC-003**: wrong_VALUE giảm so với baseline trên DevSet (đòn bẩy đánh đúng nút thắt đã chẩn đoán).
- **SC-004**: Job fine-tune hoàn tất trong giới hạn Kaggle free (thời gian/VRAM ghi rõ); tái lập
  được từ config đã lưu.
- **SC-005**: `grep` nguồn + mẫu dataset sạch `business_id ==`/`question_id ==`/tên cột hard-code;
  không câu DevSet/test nào trong data train.
- **SC-006**: Tổng tham số inference ≤15B có bằng chứng (model card); README khai báo đủ rule 8.2.
- **SC-007**: Chạy lặp inference fine-tuned 2 lần trên DevSet, `|ΔPA| ≤ 0.03`.

## 💡 Assumptions

- Cổng API free của Khang cho truy cập model lớn (≥70B lớp Llama-3.3/Qwen2.5-72B) đủ chất để sinh
  SQL đúng cho phần lớn câu number/percent; yield đủ cao để có dataset có ích (giả thuyết US1 đo —
  yield thấp thì kết luận lại, có thể đổi teacher/đơn giản hoá loại câu).
- Student **Qwen2.5-Coder-7B-Instruct** hợp lệ (Apache-2.0, phát hành 2024-11 < 26/10/2026) — **cần
  xác nhận lại license + ngày trong README trước khi chốt**; nếu không thoả, đổi base tương đương.
- QLoRA 4-bit 7B vừa 1×T4 16GB (Unsloth) — nếu không vừa, giảm seq-len/batch hoặc dùng 2×T4.
- Fine-tune dạy được kỹ năng SQL-trên-schema-runtime tổng quát, không chỉ nhớ schema train — rủi ro
  overfit được giảm bằng đa dạng business + schema-in-prompt lúc inference; `private_test` schema mới
  là phép thử thật sự (không đo được trước 20/11).
- Thời gian inference student trên 2×5090 nằm trong 6h/toàn bộ test (đã phân tích: ~1.5–3h ước cho
  ~1000 câu với vLLM) — chốt chắc ở 006 khi có Docker guideline.
- Định dạng `abstain` trong `submission.jsonl` vẫn chờ Docker guideline BTC (như 007).
- Teacher qua API ngoài chỉ dùng data-gen; mọi thứ trong Docker offline (rule 8.3) — không đổi.
