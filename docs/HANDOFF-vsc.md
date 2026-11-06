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

---
## ĐỢT 2 (2026-11-06) — Khang đã duyệt (kể cả việc tải 14B)

Quy ước như trên. Mọi phép đo: `--limit 60`, cùng seed dev, ghi vào cuối `docs/measure-007-results.md`
(mục "Đợt 2"). Với mỗi cấu hình ghi thêm: số câu hết ngân sách, s/lượt trung vị.

### Việc 3 — Few-shot với ngân sách gần thật (quan trọng nhất)
Mục tiêu: biết few-shot còn dùng được khi nộp bài thật (ngân sách 45s) hay không.

    REASONING_AGENT_TIME_BUDGET=45 python -m accuracy_boost.measure collect ... --limit 60 --fewshot-k 3
    REASONING_AGENT_TIME_BUDGET=45 python -m accuracy_boost.measure collect ... --limit 60            # baseline cùng ngân sách

Thử thêm `--fewshot-k 1` và `--fewshot-max-chars 800` (prompt ngắn hơn → nhanh hơn).

### Việc 4 — Few-shot + cổng
    python -m accuracy_boost.measure collect ... --limit 60 --fewshot-k 3 --n-runs 3
    python -m accuracy_boost.measure report --runs <file> --thresholds 0.3,0.6,1.0
(Ngân sách 240s để so với bảng cũ; nếu quá lâu thì `--limit 30` và ghi rõ.)

### Việc 5 — Qwen2.5-14B-Instruct Q4_K_M (Khang đã đồng ý tải ~9GB)
1. Tải GGUF `Qwen2.5-14B-Instruct` Q4_K_M, tạo model Ollama (ví dụ `qwen2.5-14b-ctx12k`, `num_ctx 12288`),
   cùng cách tạo `qwen2.5-7b-ctx12k`. Đặt tên model qua cấu hình/env hiện có của `reasoning_agent` (không sửa src).
2. RTX 3050 6GB sẽ offload CPU → chậm. Đo trên `--limit 20` trước (cùng 20 câu đầu của bộ dev 60),
   ngân sách `REASONING_AGENT_TIME_BUDGET=600` để lấy chất lượng, và ghi **s/lượt thật**.
3. So với 7B trên đúng 20 câu đó (baseline + few-shot k=3). Báo: PA, đúng/sai/bỏ qua, s/lượt, VRAM/RAM dùng.
4. Ước lượng: s/lượt trên 2×RTX 5090 (máy chấm) ≈ s/lượt máy dev ÷ hệ số suy ra từ băng thông/VRAM — chỉ ghi
   số đo thật và hệ số bạn giả định; để session cloud/Khang kết luận.
Không đo 14B trên 60 câu nếu 20 câu đã mất >2 giờ.

### Báo kết quả
Commit `docs: measure-007 dot 2`, push `main-868rsv`, rồi báo user "đã push".
