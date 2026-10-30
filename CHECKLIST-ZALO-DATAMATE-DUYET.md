# CHECKLIST CHỜ DUYỆT — Zalo AI Challenge: DataMate

> Gom mọi điểm cần Khang xem/quyết — tham chiếu chéo từ `TIEN_DO.md`.

## A. 👀 Nhìn nhanh (chưa có — dự án chưa có phần nào render được để "nhìn")

## B. 🧪 Thao tác thử (chưa có — chưa implement code)

## C. 💡 Quyết + đầu vào (cần Khang quyết hoặc cấp thông tin)

- [ ] C1. **Review `specs/001-data-loader/spec.md`** — xác nhận đặc tả sub-project A (data loader
  README-anchored → DuckDB) đúng ý trước khi sang `plan.md`/`tasks.md`. ⏸️ chờ Khang.
- [ ] C2. **Chọn model LLM cụ thể cho sub-project C** (reasoning agent, ≤15B tổng tham số) — chưa
  cần quyết ngay, nhưng cần quyết trước khi brainstorm sub-project `004-reasoning-agent`. ⏸️ chờ
  tới lúc đó.
- [x] ✅ C3. **Công thức chấm điểm** — đã tìm thấy trong `train/rulebook.md` §9 "Đáp án và chấm
  điểm" (file có sẵn trong dataset, không cần hỏi portal): đúng `+1`, sai `−1`, bỏ trống `0`;
  mỗi `type` có format JSON cố định (number/percent/date/boolean/string/list/table/unanswerable);
  số/percent khớp tuyệt đối (percent tròn 2 chữ số), string không phân biệt hoa-thường/khoảng
  trắng nhưng dấu tiếng Việt phải đúng, list đúng thứ tự, table so theo tên cột. Dùng thẳng §9 làm
  spec cho `003-eval-harness`, không cần giả định nữa.
- [ ] C4. **`rulebook.md` khác nhau giữa `train` và `public_test`** (train thiếu vài luật ngành
  "Mẹ và bé/Sửa xe/Điện thoại", public_test thiếu vài luật "giá nhập bình quân/tồn đơn vị lớn") →
  xác nhận với Khang: pipeline sẽ **luôn đọc `rulebook.md` kèm theo từng bộ test lúc runtime**
  (không bake cứng 1 bản vào Docker image), vì `private_test` nhiều khả năng có thêm ngành/luật
  mới. ⏸️ chờ xác nhận hướng này đúng ý trước khi sang sub-project `004-reasoning-agent`.
- [ ] C5. **7 việc Important/Minor từ final review của `001-data-loader`, hoãn tới trước
  `004-reasoning-agent`** (không chặn `002`/`003`) — chi tiết đủ trong
  `.superpowers/sdd/tasks/progress.md` phần "FINAL WHOLE-BRANCH REVIEW":
  1. Giờ trong ngày bị cắt mất khi parse cột ngày có giờ (ảnh hưởng câu hỏi ca sáng/chiều).
  2. Cột "date" lưu VARCHAR trong DuckDB, không CAST — SQL dùng EXTRACT()/date function sẽ lỗi.
  3. Header-locator fallback chọn nhầm dòng với sheet chỉ có 1 cột có dữ liệu.
  4. 7/44 README viết dạng văn xuôi, không theo format `## Cột trong` — mất lợi thế README-driven.
  5. Period-series chia theo SHEET trong 1 workbook (không phải theo FILE) chưa được gộp — FR-011
     cần mở rộng, ảnh hưởng ~209 câu hỏi ở 3 business.
  6. Số điện thoại/MST bắt đầu bằng 0 bị mất số 0 khi ép kiểu số.
  7. Vài case trùng tên cột/table hiếm còn sót (2 cột trùng tên y hệt lần 2, header rỗng "",
     cột chỉ khác hoa-thường).
  8. (Phát hiện 2026-10-30, lúc chạy full suite cho `002`) `Pandas4Warning` tại
     `build_business_db.py:97` — dựng `DataFrame` từ rows lệch độ dài ở path KHÁC path
     raw-group-merge đã fix (T10/001), hiện pandas tự pad NaN nhưng cảnh báo sẽ raise ở bản sau.
     Không fail test, chỉ warning — 55 lần lúc chạy golden test trên `train/` thật.
  ⏸️ Chưa làm — sẽ làm trước khi brainstorm `004-reasoning-agent`.
- [ ] C6. **Contract từ final review của `002-date-calendar-resolver`** (bắt buộc đọc trước khi
  brainstorm `004-reasoning-agent`): mọi hàm tính khoảng ngày của `002` trả về **CẢ kỳ** theo
  định nghĩa `rulebook.md` §2 (vd hỏi "tháng này" khi tháng đang diễn ra → trả đủ đến hết tháng
  dương lịch, KHÔNG tự cắt tại `as_of`). `004-reasoning-agent` khi dùng khoảng ngày này để lọc
  **số liệu phát sinh thực tế** (doanh thu, đơn hàng...) PHẢI tự thêm điều kiện `<= as_of` —
  002 không làm việc này. Không áp dụng cho các câu hỏi dạng "đến hết ngày X" (đã là kỳ cố định
  trong quá khứ, không cần lọc thêm). Xem chi tiết:
  `specs/002-date-calendar-resolver/spec.md` + docstring `src/date_resolver/__init__.py`.
  ⏸️ Chưa làm — ghi nhận lúc thiết kế `004-reasoning-agent`.
