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

## 1. ĐỢT 2026-10-29 (tiếp) — Thực thi `001-data-loader` bằng subagent-driven-development

- [x] ✅ `writing-plans`: viết `plan.md` + `tasks.md` (11 task T001-T011, TDD, code thật) cho
  sub-project A.
- [x] ✅ `subagent-driven-development`: thực thi đủ 11 task, mỗi task 1 implementer + 1 reviewer
  riêng. 3 lỗi thật phát hiện qua golden test trên dữ liệu thật (không phải fixture):
  - T7: table gộp mất `column_dtypes` — sửa.
  - T10 (2 vòng sửa): `split_quantity_unit` quyết định riêng từng file trên dữ liệu nhiễu → 17
    file tháng của `dev_005` chỉ gộp được 8-9/17 — sửa bằng cách gộp dữ liệu thô theo tên
    file+cột README **trước** khi làm sạch, chỉ làm sạch 1 lần → gộp đủ 17/17. Thêm guard
    header-mismatch tránh gộp sai âm thầm.
  - T11 (2 vòng sửa): bản tuần tự đúng theo plan đo được 401.6s (vượt 3.3x ngưỡng 120s) → đổi
    sang `ProcessPoolExecutor`; **đo RAM thật** (peak RSS 2.89GB, không đoán) để chốt 12 worker;
    thêm resilience khi 1 worker crash.
- [x] ✅ **Final whole-branch review** (model opus, tự chạy `build_all` trên toàn bộ `public_test`
  để kiểm, không chỉ đọc diff) — tìm ra **3 lỗi Critical** gây sai âm thầm trên dữ liệu thật:
  1. pandas 3.1.0 (chưa pin version) đổi ngữ nghĩa NaN → cột "Ghi chú" bị xoá sạch thành số.
  2. Business chỉ có file `.sqlite` (biz_123, dev_006 — ~230 câu hỏi) → loader bỏ qua, ra 0 bảng
     nhưng vẫn báo "ok".
  3. Số tiền có hậu tố `đ/k/tr` (`"1.500đ"`, `"79k"`) bị hiểu nhầm thành số lượng+đơn vị, sai tới
     1000 lần ngay trong cột doanh thu — **lật lại ruling của tôi ở Task 6** (quét ban đầu không
     bắt được case có hậu tố).
  → Dispatch 1 đợt sửa cuối (3 Critical + 2 Important liên quan: cô lập lỗi theo từng file/table,
  JSON an toàn, trùng tên table không phân biệt hoa-thường) — xem tiến độ ở
  `.superpowers/sdd/tasks/progress.md`.
- [ ] 🔜 7 việc Important/Minor còn lại hoãn tới trước `004-reasoning-agent` — xem checklist C5.
- [x] ✅ `finishing-a-development-branch` cho `001-data-loader` xong → tiếp tục brainstorm
  `002-date-calendar-resolver` trên cùng nhánh `main`.

## 2. ĐỢT 2026-10-30 — Brainstorm + thực thi `002-date-calendar-resolver`

- [x] ✅ Brainstorm (Architectural path) — quyết định sub-project 002 là **bộ hàm tính khoảng
  ngày thuần Python**, KHÔNG tự parse câu hỏi tiếng Việt (trách nhiệm đó thuộc
  `004-reasoning-agent`, 002 chỉ nhận tham số đã xác định rõ). Bám đúng `rulebook.md` §2
  "Thời gian" (đối chiếu trực tiếp cả `train/` và `public_test/`, giống nhau trừ 1 dòng
  "Trung bình mỗi ngày thứ X" chủ động để ngoài phạm vi v1).
- [x] ✅ Viết `specs/002-date-calendar-resolver/spec.md` (14 FR) — tự sửa 1 lỗi thiết kế lúc
  viết plan: bỏ tham số `as_of` thừa khỏi `tet_period`/`comparable_before_tet` (khoảng Tết năm Y
  chỉ phụ thuộc `year`, không phụ thuộc "hôm nay").
- [x] ✅ `writing-plans`: `plan.md` + `tasks.md` (5 task T001-T005, TDD) — mọi giá trị ngày trong
  test đã verify bằng Python thật trước khi viết (vd 2026-10-30 là thứ Sáu, Tết âm 2024 =
  23/12 âm 2023 → 2024-02-02 dương, mùng 10 Giêng âm 2024 → 2024-02-19 dương).
- [x] ✅ `subagent-driven-development`: thực thi đủ 5 task. Lưu ý vận hành: script
  `sdd-workspace` của skill đụng tên (cả `001` và `002` đều có file `tasks.md`, script chỉ lấy
  basename) — đã tạo workspace tay `.superpowers/sdd/002-date-calendar-resolver/` để tránh ghi
  đè ledger của 001.
  - T1 (`calendar_index.py`, 1 fix round): review tìm lỗi thật — `lunar_to_solar` bị tháng
    nhuận ghi đè âm thầm lên tháng thường cùng `(day,month,year)` (dữ liệu thật có ở tháng
    6/2025) — sửa bằng cách bỏ qua dòng `lunar_leap=true` khi xây index.
  - T2 (`date_resolver.py` phần ngày/tuần, 1 fix round): review tìm lỗi thật — `n_days_ago`
    chỉ validate giá trị (`n<1`) chưa validate kiểu (`n="5"` ra `TypeError` thay vì
    `ValueError`) — sửa + **ra ruling áp dụng xuyên Task 3**: chỉ validate kiểu tham số phụ
    domain-specific (n/month/quarter/hour), không validate kiểu `as_of`.
  - T3 (`date_resolver.py` phần tháng/quý/ca, review sạch ngay): áp đúng ruling validate kiểu
    từ T2 cho `month`/`quarter`/`hour`.
  - T4 (`tet.py`, review sạch ngay): `tet_period`/`comparable_before_tet` tra trực tiếp
    `CalendarIndex`, trả `None` (không raise) khi năm ngoài phạm vi calendar.csv.
  - T5 (`__init__.py` export 14 symbol, review sạch ngay): bề mặt public cho `004` import.
- [x] ✅ **Final whole-branch review** (model opus, tự chạy test + tự verify `tet_period` cho
  NHIỀU năm 2023-2029 trên cả `train/` và `public_test/` calendar.csv + đối chiếu từng dòng
  rulebook §2 của cả 2 bộ — không chỉ đọc diff) — tìm 3 Important:
  1. `REQUIRED_COLUMNS` thiếu cột `"lunar_leap"` dù code có đọc cột đó → CSV thiếu cột sẽ
     raise `KeyError` thô thay vì `ValueError` sạch.
  2. Thiếu test pin biên "không sau hôm nay" đúng ngày đầu tháng/quý (logic đã đúng, chỉ
     thiếu test — nếu sau này có regression `<=`→`<` sẽ lọt qua suite).
  3. (Documentation-only) Khoảng ngày trả về có thể vượt qua `as_of` (vd tháng đang diễn ra) —
     ghi rõ vào docstring: `004-reasoning-agent` phải tự lọc `<= as_of` khi dùng cho số liệu
     phát sinh thật.
  → 1 đợt sửa cuối (cả 3) + 1 scoped re-review, tất cả sạch, 42/42 test PASS.
- [x] ✅ `002-date-calendar-resolver` HOÀN TẤT — 5 task + final review + 1 fix wave, không còn
  finding mở. Xem đầy đủ ledger ở `.superpowers/sdd/002-date-calendar-resolver/progress.md`
  (workspace xoá sau khi hoàn tất, lịch sử quyết định nằm trong các dòng "Ruling:" đã chuyển
  vào đây).
- [ ] 🔜 Sau `finishing-a-development-branch` → brainstorm `003-eval-harness`.
