# ZALO AI CHALLENGE — DATAMATE — NHẬT KÝ TIẾN ĐỘ & HƯỚNG DẪN TIẾP TỤC

> Cập nhật: **2026-10-29**. Mở file này đầu tiên là biết đang ở đâu và làm gì tiếp.
> Mọi điểm chờ người quyết định đã gom về file [CHECKLIST-ZALO-DATAMATE-DUYET.md](CHECKLIST-ZALO-DATAMATE-DUYET.md).

## 📅 Deadline (ghi lại từ rule BTC)
- **Round 1 — Public test**: 26/10 – 16/11/2026, tối đa 5 submission/ngày.
- **16/11/2026 23:59 (GMT+7)**: hạn nộp **Docker package** cuối cùng (kèm checksum + Google Drive link). Tối đa 2 lần nộp, chỉ tính lần cuối.
- **Round 2 — Private test**: BTC mở 9:00 20/11, hạn nộp kết quả 23:59 23/11/2026.
- **Công bố top 2**: 02/12/2026.
- ⚠️ **Còn ~18 ngày tới hạn nộp Docker (29/10 → 16/11)** — ưu tiên có pipeline end-to-end chạy được sớm, tối ưu sau.

## 0. ĐỢT 2026-10-29 — Brainstorm & dựng nền tảng dự án

- [x] ✅ Dùng `superpowers:brainstorming` phân tích đề bài từ dữ liệu thật (`train.zip`, `public_test.zip`): xác định đây là bài Table QA/reasoning trên dữ liệu kinh doanh không đồng nhất, 3000 câu train, 8 answer type (`number/percent/list/date/string/boolean/table/unanswerable`).
- [x] ✅ Đọc đủ 8 rule kỹ thuật của BTC (offline Docker, ≤15B params tổng, không hard-code theo id, agent được sinh+chạy code, `/data` read-only, 6h trên 2×RTX5090/512GB RAM, reproducibility ΔPA≤0.03, không dùng test data để train).
- [x] ✅ Quyết định chia dự án thành 6 sub-project độc lập, thứ tự: `001-data-loader` → `002-date-calendar-resolver` → `003-eval-harness` → `004-reasoning-agent` → `005-answer-formatter` → `006-docker-packaging`.
- [x] ✅ Brainstorm xong thiết kế sub-project A (`001-data-loader`): README-anchored ETL → DuckDB, có xét và loại PySpark (dữ liệu chỉ cỡ GB, máy chấm là 1 node 512GB RAM — Spark thêm overhead JVM/Docker không cần thiết), giữ khả năng nâng cấp lên Polars/Spark sau nếu quy mô thật tăng bất ngờ.
- [x] ✅ Dựng khung project tại `D:\server-lỏ\Zalo_AI_training`: `constitution.md`, `.gitignore` (loại dataset thô + model weight khỏi git), `TIEN_DO.md`, checklist chờ duyệt.
- [x] ✅ Viết `specs/001-data-loader/spec.md` (đặc tả CÁI GÌ cho sub-project A, chưa đi kỹ thuật).
- [ ] 🔜 Khang review `spec.md` của `001-data-loader` → OK thì gọi `writing-plans` để ra `plan.md` + `tasks.md` → mới bắt đầu code.
- [ ] 🔜 Sau khi A chạy được trên toàn bộ 30 business trong `train/` → brainstorm sub-project B (date/calendar resolver).
- [ ] 🔜 Khang xác nhận máy dev nào dùng cho việc gì (laptop code logic nhẹ / máy công ty benchmark LLM) khi tới sub-project C — chưa cần quyết ngay.

## 0b. ĐỢT 2026-10-29 — Soát lại giả định "doanh nghiệp thật phức tạp hơn mẫu đã xem"

- [x] ✅ Phát hiện `rulebook.md` (có trong cả `train/` và `public_test/`, **nội dung khác nhau**
  giữa 2 bộ — train thiếu vài luật ngành public_test có, ngược lại cũng vậy) — định nghĩa chính
  xác doanh thu/công nợ/giá vốn/làm tròn/format đáp án + luật riêng theo 6 ngành (cà phê, nhà
  thuốc, vật liệu xây dựng, mẹ & bé, sửa xe, điện thoại). Giải quyết luôn checklist C3 (công thức
  chấm điểm) mà không cần hỏi portal.
- [x] ✅ Soát lại số file/business trên cả `train/` (30) và `public_test/` (14): dao động 2–24
  file/business, không phải 3-7 như mẫu ban đầu xem lúc brainstorm — kể cả `train/biz_124` đã có
  14 file. Xác nhận pattern "nhiều file cùng schema chia theo tháng" (vd `dev_005` 17 file
  `BanHang_Thang<tháng>_<năm>.xlsx`) xảy ra thật, README của business đó ghi rõ.
- [x] ✅ Dọn lỗi giải nén lồng 2 cấp (`train/train/...`, `public_test/public_test/...`) về đúng
  cấu trúc gốc trong zip (`train/...`, `public_test/...`).
- [x] ✅ Sửa `specs/001-data-loader/spec.md`: thêm FR-011 (MUST hợp nhất file cùng schema chia
  theo kỳ thành 1 table), SHOULD-012 (gợi ý khoá liên kết giữa table, không bắt buộc v1), FR-013
  (đọc `rulebook.md` kèm bộ dữ liệu, không bake cứng); cập nhật Assumptions với số liệu file/
  business thật; thêm acceptance scenario 6-7.
- [x] ✅ Sửa `constitution.md`: thêm cảnh báo `rulebook.md` là dữ liệu runtime (đổi theo từng bộ
  test), không phải kiến thức tĩnh bake vào Docker/prompt.
- [ ] 🔜 Khang xác nhận checklist **C4** (đọc rulebook.md runtime từ `/data`, không hardcode) —
  đúng hướng chưa, trước khi sang `writing-plans` cho `001-data-loader`.
