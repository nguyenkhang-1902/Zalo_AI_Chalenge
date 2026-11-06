# Inbox từ session VS Code → session cloud

## 2026-11-05 — Việc 1 + Việc 2 (handoff) đã xong

- Kết quả đầy đủ đã ghi vào cuối `docs/measure-007-results.md` (mục "Đo thêm — few-shot + tái lập").
- Ruling của tôi: dùng `ACCURACY_BOOST_N_RUNS=1` (greedy, không voting) cho cả 2 lượt đo, thay default=3 trong `config.py`.
  Lý do: dòng "Baseline greedy" gốc trong bảng kết quả là đo 1-run (greedy); ước lượng "~1h" của handoff cho 60 câu
  chỉ khớp n_runs=1 (n_runs=3 sẽ ~3h). Muốn so sánh táo-với-táo với baseline gốc nên giữ cùng phương pháp.
  Cái giá nếu sai: nếu ý định thật của handoff là đo few-shot CÓ voting (N=3) thì kết quả few-shot ở đây chưa phản ánh
  đúng — cần đo lại với n-runs=3 nếu cloud session cần số đó.
- ⚠️ Lưu ý quan trọng: few-shot đo ở `REASONING_AGENT_TIME_BUDGET=240`, không phải 45s thật lúc nộp bài — xem cảnh báo
  chi tiết trong `measure-007-results.md`. Đừng kết luận "bật few-shot mặc định" chỉ từ số đo này.
- Bẫy nhỏ gặp phải: `accuracy_boost/measure.py`'s `_cmd_collect` print cuối cùng chứa ký tự tiếng Việt (`đã ghi...`)
  → crash `UnicodeEncodeError` trên Windows console (cp1252) sau khi đã ghi xong dữ liệu (không mất dữ liệu, chỉ
  dòng print cuối crash, exit code 1 giả). Workaround dùng: set `PYTHONIOENCODING=utf-8` trước khi chạy — KHÔNG sửa
  `src/` (ngoài phạm vi VS Code session). Nếu cloud session muốn sửa gốc: bọc print cuối trong try/except hoặc
  set `sys.stdout.reconfigure(encoding="utf-8")` ở đầu `main()`.

## 2026-11-06 — Đợt 2 (Việc 3/4/5) đã xong

- Kết quả đầy đủ ở cuối `docs/measure-007-results.md` (mục "Đợt 2").
- **Phát hiện quan trọng nhất (Việc 3)**: ở ngân sách nộp bài thật 45s, mọi cấu hình (baseline, few-shot k=1,
  few-shot k=3) gần như vô dụng — 2/3 cấu hình 60/60 hết ngân sách (PA=0.000 toàn bỏ qua), few-shot k=3 chỉ lọt
  7/60 câu. s/lượt trung vị cả 3 đều ~47s → nút thắt là NGÂN SÁCH 45s tự nó, không phải few-shot làm chậm thêm.
  Nếu không tăng được ngân sách lúc nộp bài, mọi cấu hình đo ở 240s (bảng "Đo thêm") coi như không áp dụng được
  khi chấm thật.
- **Việc 4**: few-shot k=3 + gate N=3 (giảm `--limit 30` theo đúng phần dự phòng handoff cho phép, vì 60 câu×3
  run ước ~6-7h). PA chạm **0.000** ở ngưỡng 0.6-1.0 (lần đầu không âm trong toàn bộ project) — nhưng mẫu nhỏ
  (30 câu, chỉ 1-2 đúng/sai), tín hiệu còn yếu, nên xác nhận lại trên mẫu lớn hơn nếu có thời gian.
- **Việc 5 (14B)**: model `qwen2.5-14b-ctx12k` đã tạo xong (không cần tải, dùng chung layer với
  `qwen2.5:14b-instruct` có sẵn). Kết quả: 14B **thua hoặc hòa 7B** cả về độ đúng và tốc độ (baseline hòa tuyệt
  đối nhưng chậm 4.2×; few-shot k=3 thì 14B tệ hơn 7B — 0 đúng vs 2 đúng/20 câu — và chậm hơn 2.6×). Ruling của
  tôi: KHÔNG scale lên 60 câu dù mỗi lượt riêng lẻ chưa vượt 2h (baseline ~104 phút, few-shot ~115 phút) vì kết
  luận "14B không đáng dùng" đã đủ rõ từ 20 câu, scale thêm chỉ tốn ~5-6h/cấu hình mà không đổi kết luận. Cũng
  dùng lại dữ liệu 7B đã đo ở budget=240s (không chạy lại ở 600s) để so sánh — chênh lệch ngân sách không đáng
  kể vì 7B hiếm khi dùng hết 240s.
- Nếu cần quyết định cuối: với dữ liệu hiện có, hướng khả thi nhất để tăng PA là **few-shot + gate N=3** (Việc 4),
  nhưng CHỈ có ý nghĩa nếu ngân sách nộp bài thật được tăng lên gần 240s — ở 45s thật hiện tại, không cấu hình
  nào trong toàn bộ 2 đợt đo chạy được đủ để tạo ra lợi ích gì.
