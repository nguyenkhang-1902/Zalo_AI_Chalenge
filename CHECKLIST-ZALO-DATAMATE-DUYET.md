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
- [ ] C6. **Contract từ final review của `002-date-calendar-resolver`** (bắt buộc đọc trước khi
  brainstorm `004-reasoning-agent`): mọi hàm tính khoảng ngày của `002` trả về **CẢ kỳ** theo
  định nghĩa `rulebook.md` §2 (vd hỏi "tháng này" khi tháng đang diễn ra → trả đủ đến hết tháng
  dương lịch, KHÔNG tự cắt tại `as_of`). `004-reasoning-agent` khi dùng khoảng ngày này để lọc
  **số liệu phát sinh thực tế** (doanh thu, đơn hàng...) PHẢI tự thêm điều kiện `<= as_of` —
  002 không làm việc này. Không áp dụng cho các câu hỏi dạng "đến hết ngày X" (đã là kỳ cố định
  trong quá khứ, không cần lọc thêm). Xem chi tiết:
  `specs/002-date-calendar-resolver/spec.md` + docstring `src/date_resolver/__init__.py`.
  ⏸️ Chưa làm — ghi nhận lúc thiết kế `004-reasoning-agent`.
