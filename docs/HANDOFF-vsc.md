# Giao việc cho session VS Code (máy dev, có Ollama + train/)

Kênh trao đổi: git, nhánh `main-868rsv`. Session VS Code: `git pull origin main-868rsv` trước khi làm.
Quy ước file: VS Code chỉ sửa `docs/measure-*.md` và `docs/inbox-vsc.md`; session cloud sửa `src/`, `TIEN_DO.md`, checklist.

## Việc 1 — Đo few-shot (~1h)
Điều kiện: Ollama chạy model `qwen2.5-7b-ctx12k`, `REASONING_AGENT_TIME_BUDGET=240`, `PYTHONPATH=src`.
Dùng đúng `--dataset-dir`, `--size`, `--limit 60` như lần đo trước (bảng ở `measure-007-results.md`):

    python -m accuracy_boost.measure collect --dataset-dir <như lần trước> --out <runs_fewshot.jsonl> --limit 60 --fewshot-k 3
    python -m accuracy_boost.measure report --runs <runs_fewshot.jsonl> --thresholds 0.3,0.6,1.0

## Việc 2 — Kiểm tái lập
Chạy lại baseline greedy (không cờ) 60 câu lần 2; ghi |ΔPA| so với -0.717 (đạt nếu <= 0.03).

## Báo kết quả
Thêm vào cuối `docs/measure-007-results.md` một bảng: cấu hình | PA | đúng | sai | bỏ qua | s/lượt,
cộng 1–2 dòng nhận xét. Commit `docs: measure-007 few-shot + repro`, push, rồi báo user "đã push".
KHÔNG tải 14B-Q4 khi chưa hỏi Khang. KHÔNG push lên nhánh khác.
