# CHECKLIST CHỜ DUYỆT — Zalo AI Challenge: DataMate

> Gom mọi điểm cần Khang xem/quyết — tham chiếu chéo từ `TIEN_DO.md`.

## A. 👀 Nhìn nhanh (chưa có — dự án chưa có phần nào render được để "nhìn")

## B. 🧪 Thao tác thử (chưa có — chưa implement code)

## C. 💡 Quyết + đầu vào (cần Khang quyết hoặc cấp thông tin)

- [x] ✅ C1. **Review `specs/001-data-loader/spec.md`** — Khang duyệt ("tạm thời chưa phát hiện
  thêm gì cần sửa"), đã chạy `writing-plans` + `subagent-driven-development`, `001-data-loader`
  hoàn tất.
- [x] ✅ C2. **Model LLM cho `004-reasoning-agent`** — Khang chọn (2026-10-30):
  **Qwen2.5-14B-Instruct** (hoặc bản Qwen3-14B mới hơn nếu có lúc build) làm model ĐÍCH chạy
  trong Docker nộp thật (multilingual tiếng Việt + code-gen tốt nhất ở tier 14B, tận dụng gần
  hết ngân sách 15B). Quyết định kèm theo: dev/test logic bằng **Qwen2.5-7B-Instruct chạy local**
  (máy công ty RTX 3050 6GB không đủ VRAM ổn định cho 14B), chỉ swap sang bản 14B lúc đóng Docker
  cuối (`006-docker-packaging`) — vì vậy **004 PHẢI thiết kế model-agnostic** (tên model qua
  config/env var, không hard-code), không chặn việc đổi model sau này.
- [x] ✅ C3. **Công thức chấm điểm** — đã tìm thấy trong `train/rulebook.md` §9 "Đáp án và chấm
  điểm" (file có sẵn trong dataset, không cần hỏi portal): đúng `+1`, sai `−1`, bỏ trống `0`;
  mỗi `type` có format JSON cố định (number/percent/date/boolean/string/list/table/unanswerable);
  số/percent khớp tuyệt đối (percent tròn 2 chữ số), string không phân biệt hoa-thường/khoảng
  trắng nhưng dấu tiếng Việt phải đúng, list đúng thứ tự, table so theo tên cột. Dùng thẳng §9 làm
  spec cho `003-eval-harness`, không cần giả định nữa.
- [x] ✅ C4. **`rulebook.md` khác nhau giữa `train` và `public_test`** — Khang xác nhận
  (2026-10-30): pipeline luôn đọc `rulebook.md` kèm theo từng bộ test lúc runtime, không bake
  cứng vào Docker image. Đã implement đúng hướng này từ `001` (passthrough copy trong
  `build_all.py`), `002`/`003` không đụng `rulebook.md` trực tiếp nhưng không vi phạm.
- [x] ✅ C5. **8 việc Important/Minor từ final review của `001-data-loader`** — ĐÃ SỬA +
  RE-VERIFY đầy đủ trên dữ liệu thật 2026-10-31 (8 task hardening, chi tiết số liệu ở
  `TIEN_DO.md` mục 4, ledger đầy đủ `.superpowers/sdd/c5-hardening-tasks/`):
  1. ✅ Giờ trong ngày bị cắt mất khi parse cột ngày có giờ — sửa Task 1 (`d9777c2`).
  2. ✅ Cột "date" lưu VARCHAR trong DuckDB, không CAST — sửa Task 1 (`d9777c2`), nay là
     `DATE`/`TIMESTAMP` native.
  3. ✅ Header-locator fallback chọn nhầm dòng với sheet chỉ có 1 cột có dữ liệu — sửa Task 3
     (`ed4affa`).
  4. ✅ 7/44 README viết dạng văn xuôi — xác nhận Task 7 (`88c6b84`): không cần sửa README
     parser, cả 7 business vẫn load đúng qua fallback header-locator sau fix #3 — 7/7 PASSED.
  5. ✅ Period-series chia theo SHEET trong 1 workbook (15 business ảnh hưởng, xem đính chính
     2026-10-31 dưới) chưa được gộp — sửa Task 6 (`5f37a7a` + `69aba00`). Verify thật trên dữ
     liệu thật (Task 8): `biz_102` → 1 table `DonHang_ChiTiet` (18 source_files); `biz_105` →
     1 table `SoBanHang` (17 source_files, xuyên 2 file); `dev_014` → 1 table `SoBanHang` gộp +
     1 table riêng `SoBanHang__Ghi tắt` cho sheet lạc — khớp 100% kỳ vọng.
     **Đính chính 2026-10-31** (quét lại đủ toàn bộ `.xlsx`, lần trước bị crash giữa đường ở
     `biz_116`): ảnh hưởng **15 business**, không phải 3 như ghi nhận gốc —
     `train`: biz_102, 103, 105 (2 file), 112, 115, 117, 118, 119, 120, 122, 128 (11 business);
     `public_test`: dev_004, dev_012, dev_013 (2 file), dev_014 (4 business). Các workbook nhiều
     sheet KHÔNG phải period-series (không đụng fix này): biz_109, biz_116, biz_121, dev_003,
     dev_013/QuanLy.xlsx.
  6. ✅ Số điện thoại/MST bắt đầu bằng 0 bị mất số 0 khi ép kiểu số — sửa Task 2 (`d436a00`,
     review fix `5a24b16`).
  7. ✅ Vài case trùng tên cột/table hiếm còn sót (2 cột trùng tên y hệt lần 2, header rỗng "",
     cột chỉ khác hoa-thường) — sửa Task 4 (`3ac29af`).
  8. ✅ `Pandas4Warning` tại `build_business_db.py:97` khi dựng `DataFrame` từ rows lệch độ dài
     — sửa Task 5 (`ae5f9f9` + `51a7994`). Verify thật Task 8: `build_all` full `train/` +
     `public_test/` với `Pandas4Warning` promote thành lỗi cứng → chạy xong KHÔNG lỗi.
  **Verify tổng (Task 8, 2026-10-31)**: `pytest tests/data_loader/` → **59 passed, 1 failed**
  (fail là Finding mới #9 ⚠️ dưới, không phải regression); `build_all` thật trên `train` +
  `public_test` → `train: 30 business, not-ok: {}` / `public_test: 14 business, not-ok: {}`
  (SC-001 giữ nguyên, không business nào crash).
  - [ ] ⚠️ **Finding mới #9 (ngoài phạm vi C5, phát hiện 2026-10-30→31, KHÔNG fix trong Task 8)**
    — ngân sách 120s của golden test `test_builds_entire_train_dataset_within_time_budget`
    (SC-003) quá sát khi máy chạy nhiều subagent song song kéo dài nhiều giờ — quan sát lặp lại
    nhiều lần (99.7s, 123.1s, 134.8s, 148.9s, 155.8s, 162s, 168.7s) xuyên suốt cả 8 task hardening.
    CŨNG fail trên baseline CHƯA sửa gì (`a4feb96`), xác nhận độc lập bằng git-stash A/B testing
    bởi cả Task 1 và Task 3 → môi trường/máy bị áp lực CPU/RAM tích lũy, KHÔNG phải code
    regression của 8 fix C5. Cần đo lại SC-003 trên máy rảnh, Khang quyết giữ 120s hay nới ngân
    sách.
- [x] ✅ C6. **Contract từ final review của `002-date-calendar-resolver`**: mọi hàm tính khoảng
  ngày của `002` trả về **CẢ kỳ** theo định nghĩa `rulebook.md` §2, `004-reasoning-agent` khi
  dùng khoảng ngày này để lọc **số liệu phát sinh thực tế** phải tự thêm điều kiện `<= as_of`.
  **Đã làm**: `004`'s `date_tools.py` tự thêm `query_end = min(end, as_of_date)` cho 11/12 tool
  (ngoại lệ `shift_session`, không có khái niệm khoảng ngày) — xem FR-004 +
  `specs/004-reasoning-agent/reasoning-agent-plan.md` mục "Đính chính lúc viết plan".

- [ ] C8. **Hướng đi sau Q&A của BTC (2026-11-03) — Khang quyết.** BTC cho phép fine-tune/distill
  bằng LLM lớn hoặc API ngoài + data tự sinh (không dùng public_test), miễn đóng gói cả train + data
  và inference offline ≤15B (LoRA tính vào). Mở ra 3 hướng cho vấn đề accuracy ~10% của C7:
  (a) bỏ fine-tune, chỉ đổi model 14B + few-shot lấy từ `train/` (rẻ, ít rủi ro, trần thấp);
  (b) rejection-sampling fine-tune: teacher mạnh (API) sinh quỹ đạo tool-call trên câu hỏi train,
  lọc bằng `answers.jsonl`, SFT/LoRA cho model ≤15B (khuyến nghị, cần GPU thuê để train);
  (c) kết hợp: làm (a) trước làm baseline an toàn, rồi (b) nếu còn thời gian.
  Việc cần làm bất kể hướng nào: kiểm tính tất định batch trên Docker thật; chờ Docker guideline.
  ✅ **Khang chọn (c) kết hợp (2026-11-03)**: làm (a) trước làm baseline an toàn, rồi (b) nếu còn
  thời gian. Chưa duyệt spec/plan → chưa code.
  📌 **Ràng buộc nguồn lực (Khang xác nhận 2026-11-03)**: chỉ có máy hiện tại (RTX 3050 6GB /
  laptop 16GB), KHÔNG có GPU thuê, KHÔNG có API teacher. → (b) fine-tune/distill coi như hoãn
  (chỉ còn đường self-distill + Kaggle/Colab free, rủi ro cao); trọng tâm là (a) mở rộng không cần
  train: đo 14B-Q4 qua llama.cpp, few-shot từ `train/`, semantic-layer tool, abstain theo độ tin cậy.
  📊 **Kết quả đo 007 (60 câu dev, 2026-11-04)**: baseline PA -0.717; cổng N=3 ngưỡng 1.0 PA -0.283 (giảm
  lỗ, không dương); semantic tools PA -0.617. Kết luận: 7B không-train chỉ ~2–3% đúng. Chi tiết:
  `docs/measure-007-results.md`. Đo thêm (2026-11-05): tái lập đạt (ΔPA=0); few-shot k=3 PA -0.333,
  5/60 đúng (8.3%) nhưng chậm, cần đo lại ở ngân sách 45s. Chưa đo: 14B-Q4 (cần Khang đồng ý tải ~9GB).
- [ ] C7. **`004-reasoning-agent` Task 1-6 xong, review clean (40/40 test); Task 7 (baseline thật
  100 câu) lộ ra máy dev hiện tại (RTX 3050 6GB) không đủ mạnh để đo accuracy thật đáng tin —
  Khang đã tạm chấp nhận (2026-11-03), ghi lại để quyết dứt điểm trước khi nộp Docker thật.**
  - Lần chạy đầu (commit `0aa0767`, model `qwen2.5:7b-instruct` ctx mặc định ~4096): 96/96 câu
    hết ngân sách 45s/6-step → accuracy 12.5% (12/96, toàn bộ là trùng ngẫu nhiên với câu
    ground-truth vốn đã "unanswerable" — accuracy thật trên 84 câu còn lại = 0%).
  - Root cause xác nhận: context mặc định (~4096) quá nhỏ so với system prompt thật (6374 token
    cho `biz_102` + 15 tool) → model/Ollama xử lý cực chậm (180s-300s+/lượt gọi, có lúc không
    bao giờ xong). KHÔNG phải lỗi code Task 1-6, KHÔNG phải "zombie GPU job" (loại trừ bằng thực
    nghiệm riêng) — đơn thuần context quá nhỏ cho prompt quá dài trên GPU 6GB.
  - Fix hạ tầng (KHÔNG sửa code, chỉ operator-config, giữ đúng thiết kế model-agnostic
    OpenAI-compatible): tạo model tag riêng `qwen2.5-7b-ctx12k` qua `ollama create` (Modelfile
    thêm `PARAMETER num_ctx 12288`, dùng lại blob có sẵn, không tải thêm). Xác nhận: lượt gọi ấm
    (warm) với prompt giống nhau chỉ mất **6.2s** (Ollama cache 6373/6374 token prompt).
  - Fix prompt (commit `d8b2a2f`): model hay đoán sai/dịch sai tên cột SQL (`DateOfOrder` không
    tồn tại, `Thành tiền` thay vì `Tổng tiền` thật) + thiếu dấu ngoặc kép cho tên cột nhiều từ —
    sửa `prompt.py` hiển thị tên cột có sẵn dấu ngoặc kép + cảnh báo rõ + ví dụ SQL đúng.
  - **Kết quả sau cả 2 fix** (test lại đúng 10 câu mẫu, seed=42, chấm qua `score_submission`
    thật): accuracy vẫn **1/10 (10%)** — vẫn chỉ đúng câu "unanswerable" trùng ngẫu nhiên. NHƯNG
    pipeline khỏe hơn rõ: 3/10 câu giờ hoàn thành trong ngân sách và ra đáp án số thật (trước đó
    0/10) — vấn đề treo/hết ngân sách do đoán sai tên cột đã giảm đáng kể. Cả 3 câu hoàn thành
    đều **sai giá trị** → lộ lớp vấn đề mới, sâu hơn: model 7B suy luận sai logic nghiệp vụ (sai
    khoảng ngày, sai công thức tổng hợp, hoặc thiếu điều kiện lọc trạng thái theo rulebook) —
    không còn là lỗi hạ tầng/tên cột, mà là giới hạn khả năng suy luận của model nhỏ trên GPU yếu.
  - ⏸️ **Khang tạm chấp nhận hiện trạng (2026-11-03)**: coi `004` xong về code + hạ tầng (Task
    1-6 logic đúng, unit test clean; Task 7 hạ tầng đã hết crash/treo), chuyển sang
    `005-answer-formatter`/`006-docker-packaging`. **Cần quyết lại trước khi nộp Docker thật**:
    đo lại accuracy với model mạnh hơn (14B, cần hạ tầng tốt hơn GPU 6GB hiện tại) hoặc tiếp tục
    lặp prompt/kiến trúc — việc này KHÔNG phải sửa lỗi nhanh, là vòng đánh giá LLM mở.
  - Chi tiết đầy đủ (log/trace từng lượt gọi, số liệu thật): ledger
    `.superpowers/sdd/reasoning-agent-tasks/progress.md`.
