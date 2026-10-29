# HIẾN PHÁP DỰ ÁN — Zalo AI Challenge 2026: DataMate

> `constitution.md` · phiên bản 1.0 · theo Spec-Driven Development
> Nền tảng bất biến mọi spec/plan/task phải tuân. Xung đột → hiến pháp thắng.

## 0. 🧭 Bối cảnh dự án

Dự án cá nhân (solo) của Nguyễn Khang tham gia **Zalo AI Challenge 2026 — track DataMate**
(`https://challenge.zalo.ai/portal/datamate`). Đề bài: cho 1 câu hỏi tiếng Việt tự nhiên +
`business_id` + `as_of_date`, hệ thống phải đọc dữ liệu kinh doanh thô (Excel/CSV, schema khác
nhau mỗi doanh nghiệp) + `README.md` mô tả cột/quy ước, rồi tính ra đáp án đúng (number, percent,
list, date, string, boolean, table, hoặc unanswerable).

**KHÔNG làm gì**: không xây UI/web cho người dùng cuối, không làm sản phẩm chạy liên tục (chỉ là
1 lần chạy batch theo lệnh BTC), không dùng public/private test data để train/fine-tune model,
không có bất kỳ logic khoá theo `business_id`/`question_id` cụ thể.

⚠️ **`rulebook.md` là dữ liệu runtime, KHÔNG phải kiến thức tĩnh**: mỗi bộ dữ liệu
(`train/`, `public_test/`, sau này `private_test/`) có kèm 1 `rulebook.md` định nghĩa chính xác
doanh thu/công nợ/giá vốn/luật theo ngành + cách chấm điểm — đã xác nhận train và public_test có
**nội dung khác nhau** (public_test có thêm luật ngành train không có, và ngược lại). `private_test`
nhiều khả năng có thêm ngành/luật mới. → Pipeline PHẢI đọc `rulebook.md` từ chính bộ dữ liệu được
mount vào `/data` lúc chạy, không bake cứng 1 bản nào vào Docker image hay prompt tĩnh.

### Đọc trước khi dựng
1. Spec là nguồn sự thật — trình tự constitution → specify → clarify → plan → tasks → analyze → implement.
2. Làm từng sub-project (xem mục "Quy tắc riêng"), human-in-the-loop mỗi mốc — brainstorm trước, code sau.
3. Đọc `README.md` của từng business + dữ liệu mẫu thật trước khi viết logic xử lý — không tự bịa cấu trúc dữ liệu.
4. 🔒 Không bao giờ commit bí mật (không áp dụng nhiều vì không có service/API key, nhưng vẫn áp dụng cho mọi credential phát sinh sau).
5. ⚠️ Không test trên oán định `private_test` khi nó được công bố (20/11) — chỉ dùng để chạy final, không dùng để sửa logic/train lại.
6. Gặp mơ hồ về luật cuộc thi → hỏi/đọc lại rule trên portal, không đoán.

## 🏛️ Core Principles (NON-NEGOTIABLE)

### Điều 1 — Đơn giản & dùng tính năng sẵn có
KISS/YAGNI. Ưu tiên DuckDB/pandas/stdlib trước khi tự viết parser riêng. Không thêm engine
nặng (Spark, distributed system) khi dữ liệu còn ở quy mô single-machine (xem research.md
sub-project A — lý do chọn DuckDB thay PySpark).

### Điều 2 — Nghiệm thu rõ ràng
Mỗi sub-project có eval harness đo bằng chính `train/answers.jsonl` trước khi coi là "xong".
Không báo done chỉ vì "code chạy không lỗi" — phải có số liệu accuracy/coverage cụ thể.

### Điều 3 — Đặt tên nhất quán
Code Python: `snake_case`. Tên cột/table trong DuckDB giữ nguyên tiếng Việt có dấu từ README
(vì semantics phụ thuộc đúng từ gốc) — không dịch sang tiếng Anh, không bỏ dấu.

### Điều 4 — Hằng số thay magic value
Mọi ngưỡng (confidence threshold header-locator, time budget mỗi câu hỏi, số retry code-exec...)
để ở `config.py`/`.env`, không hard-code rải trong logic.

### Điều 5 — Kỷ luật cấu trúc
Một trách nhiệm/module (loader khác reasoning-agent khác formatter). File Python dùng
`snake_case` dài đủ để đoán nội dung không cần mở file. Tách khi file vượt ~250 dòng, trần cứng 700 dòng.

### Điều 6 — Tài liệu hoá
`research.md` mỗi sub-project ghi rõ lý do chọn kỹ thuật + sổ bẫy dữ liệu (vd: cột số lẫn
string có dấu phẩy, số lượng kèm đơn vị, header không ở dòng 1).

### Điều 7 — Thiết kế cho quy mô & suy giảm duyên dáng
1 file/sheet lỗi không được làm sập cả pipeline của 1 business — bỏ qua table lỗi, log rõ,
các table khác vẫn dùng được. Có timeout/budget rõ ràng mỗi câu hỏi để không vượt 6h tổng.

### Điều 8 — Ưu tiên nền tảng/thư viện đã kiểm chứng
DuckDB, pandas, openpyxl, một local LLM runtime (llama.cpp/vLLM/Ollama-compatible) đã có
cộng đồng lớn — tránh thư viện lạ ít người dùng cho phần lõi.

### Điều 9 — Output rõ ràng, có log để chứng minh reproducibility
Không có UI, nhưng mọi lần chạy phải ghi log đủ để giải thích lại kết quả khi BTC yêu cầu
(rule 8: |PA(upload) − PA(re-run)| ≤ 0.03). Giảm phần ngẫu nhiên (temperature thấp/0, seed cố định).

### Điều 10 — 🔒 Tuân thủ tuyệt đối luật cuộc thi
Không hard-code theo `business_id`/`question_id`. Không gọi API ngoài/internet trong Docker.
Tổng tham số mọi model dùng lúc inference ≤ 15B. Không dùng test data để train.

### Điều 11 — Giữ nguyên ngữ cảnh tiếng Việt
Dữ liệu, README, câu hỏi đều tiếng Việt (có dấu, không dấu, viết tắt lẫn lộn như "bnhiu",
"thang 7/2026") — pipeline phải chịu được input tiếng Việt lộn xộn, không chuẩn hoá mất nghĩa.

## ⚙️ Nền tảng & hạ tầng (đã chốt)

- **Ngôn ngữ**: Python (toàn bộ pipeline).
- **Data layer**: DuckDB (xem Điều 1) + pandas/openpyxl cho bước đọc Excel thô.
- **Model**: LLM local, tổng tham số ≤15B tại thời điểm inference (chọn cụ thể ở sub-project C).
- **Đóng gói**: Docker image offline, không network, data mount read-only tại `/data`,
  output ghi `/result/submission.jsonl`.
- **Máy chấm chính thức**: 2× NVIDIA RTX 5090 (32GB VRAM/card), 512GB RAM — pipeline phải
  chạy xong toàn bộ private test trong 6h kể cả thời gian load model.
- **Máy dev**: laptop cá nhân (16GB RAM, không GPU dùng được cho LLM) để code/test logic nhẹ;
  máy công ty (32GB RAM, RTX 3050 6GB) để benchmark model LLM thật nặng hơn khi cần.
- **Dataset thô** (`train/`, `public_test/`, sau này `private_test/`): **KHÔNG commit vào git**
  (quá lớn, luôn tải lại được từ portal) — nằm trong `.gitignore`.

## ➕ Quy tắc riêng của dự án Zalo DataMate

1. **Bối cảnh & phạm vi**: dự án solo của Khang, mục tiêu lọt top kết quả Zalo AI Challenge
   2026 — DataMate. Không làm UI, không làm service chạy liên tục — chỉ 1 pipeline batch
   đóng gói Docker chạy 1 lần/lượt chấm.
2. **Nền tảng & hạ tầng đã chốt**: xem mục "⚙️ Nền tảng & hạ tầng" trên. Không có hệ thống
   nào khác đang chạy cần tránh đụng vào (dự án mới hoàn toàn, thư mục riêng).
3. **Nguồn dữ liệu & đồng bộ**: dữ liệu tĩnh do BTC cấp qua `train.zip`/`public_test.zip`
   (đã giải nén tại `train/`, `public_test/`), sau này `private_test` công bố 20/11. Không
   đồng bộ 2 chiều với hệ thống nào — chỉ đọc 1 lần/lượt chấm.
4. **Phân quyền**: không áp dụng — không có người dùng cuối, hệ thống chấm hoàn toàn tự động.
5. **Vận hành định kỳ**: không có job nền. Chỉ chạy khi BTC invoke Docker (1 lần/lượt chấm) —
   lúc dev, chạy eval harness thủ công theo nhu cầu, không đặt cron.
6. **Backup & khôi phục**: code backup qua git (local, push lên remote cá nhân khi cần —
   xác nhận trước khi push theo CLAUDE.md). Dữ liệu thô không backup riêng — tải lại từ portal
   nếu mất, vì luôn sẵn có ở đó.
7. **Người duyệt cuối**: Nguyễn Khang (solo) — mọi điểm mơ hồ gom vào
   `CHECKLIST-ZALO-DATAMATE-DUYET.md`.
8. **Ràng buộc đặc thù cuộc thi** (8 rule chính thức từ BTC, không thương lượng):
   1. Tuân quy chế chung Zalo AI Challenge 2026 + điều kiện dự thi.
   2. Model dùng lúc inference (LLM/embedding/reranker/classifier...) cộng lại ≤ **15 tỷ tham số**
      (tính cả MoE đầy đủ tham số), weight phải public trước 01/10/2026, licence cho phép dùng,
      được fine-tune tự do, quantize tự do. Phải khai báo model trong README của solution.
   3. **Không gọi API/service ngoài** — Docker chạy hoàn toàn offline, mạng bị tắt khi BTC chạy.
   4. **Không human-in-the-loop** — không hard-code đáp án, không logic khoá theo
      `business_id`/`question_id`.
   5. Agent **được** sinh + chạy code trong container (khuyến khích nhưng không bắt buộc).
      `/data` mount read-only — ghi file tạm ở nơi khác.
   6. Chỉ được dùng: data BTC cấp cho train, data tự synthesize, dataset/model public khác.
      **Tuyệt đối không** dùng public/private test data để train hoặc thu thập đáp án test
      bằng bất kỳ cách nào.
   7. **Compute reference**: 2×RTX5090 (32GB/card, 64GB tổng), 512GB RAM. Phải xử lý xong
      toàn bộ private test trong **6 giờ** wall-clock (tính cả thời gian load model). Blackwell
      GPU cần CUDA ≥12.8 + bản PyTorch/vLLM tương ứng (theo Docker guideline riêng của BTC).
   8. **Reproducibility**: điểm của lượt BTC tự re-run trên private test là điểm cuối cùng.
      Phải tất định đủ để `|PA(nộp) − PA(re-run)| ≤ 0.03`; lệch quá ngưỡng → BTC xem log,
      có thể re-run lại hoặc disqualify nếu không giải thích được.

## 🔁 Quy trình Spec-Driven (cách dùng hiến pháp này)

```
constitution (xong) → specify (spec.md mỗi sub-project) → clarify → plan → tasks
                     → analyze → implement → quay lại cho sub-project kế tiếp
```

**Thứ tự sub-project đã chốt** (xem `specs/`):
`001-data-loader` (A) → `002-date-calendar-resolver` (B) → `003-eval-harness` (E)
→ `004-reasoning-agent` (C) → `005-answer-formatter` (D) → `006-docker-packaging` (F)

## 🏛️ Governance

- Đứng trên mọi spec/plan/task/config trong dự án này.
- Sửa đổi: ghi lý do, tăng version (MAJOR đổi/bỏ nguyên tắc · MINOR thêm · PATCH chỉnh chữ),
  cập nhật ngày.
- Phát hiện phải vi phạm 1 điều để khả thi → dừng, tự Khang quyết (solo, mục 7).

**Version**: 1.0 | **Ratified**: 2026-10-29 | **Last Amended**: 2026-10-29
> 📅 Changelog: v1.0 (2026-10-29) — Khởi tạo hiến pháp dự án, chốt luật cuộc thi + thứ tự 6 sub-project.
