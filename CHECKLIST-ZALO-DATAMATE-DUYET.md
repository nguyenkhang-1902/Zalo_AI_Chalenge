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
