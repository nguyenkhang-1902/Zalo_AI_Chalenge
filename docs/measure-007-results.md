# Kết quả đo 007 — 60 câu dev (từ train/), model qwen2.5-7b-ctx12k, 2026-11-04

Cấu hình đo: `REASONING_AGENT_TIME_BUDGET=240` (mặc định nộp bài vẫn 45s). Lần đo đầu với 45s
không hợp lệ (180/180 hết ngân sách; Ollama còn kẹt hàng đợi + 45s quá chặt cho RTX 3050 6GB).

| Cấu hình | PA | đúng | sai | bỏ qua | s/lượt |
|---|---|---|---|---|---|
| Baseline greedy | -0.717 | 1 | 44 | 15 | 59.9 |
| Gate N=3, ngưỡng 0.3 | -0.783 | 2 | 49 | 9 | |
| Gate N=3, ngưỡng 0.6 | -0.517 | 1 | 32 | 27 | |
| Gate N=3, ngưỡng 1.0 | -0.283 | 1 | 18 | 41 | |
| Semantic tools, greedy | -0.617 | 2 | 39 | 19 | 74.9 |

## Kết luận
- Độ đúng của 7B không-train chỉ ~2–3%; PA âm ở mọi cấu hình. Cổng chỉ giảm lỗ, không tạo điểm dương.
- Semantic tools: +1 câu đúng (trong nhiễu), chậm hơn ~25% → chưa đủ lý do bật mặc định.
- Chưa đo: few-shot, tái lập (|ΔPA| ≤ 0.03), 14B-Q4 (cần hỏi Khang trước khi tải ~9GB).
- Nút thắt là năng lực model (sai giá trị dù đúng kiểu), không phải cổng/tool.
