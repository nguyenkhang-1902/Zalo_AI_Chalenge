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
