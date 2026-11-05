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

## Đo thêm — few-shot + tái lập (2026-11-05, máy VS Code, cùng 60 câu dev seed=42)

| Cấu hình | PA | đúng | sai | bỏ qua | s/lượt |
|---|---|---|---|---|---|
| Few-shot k=3, greedy | -0.333 | 5 | 25 | 30 | 134.5 |
| Baseline greedy (lần 2, kiểm tái lập) | -0.717 | 1 | 44 | 15 | 83.7 |

### Nhận xét
- **Tái lập đạt**: lần 2 ra đúng y lần 1 (1 đúng/44 sai/15 bỏ qua, PA -0.717) → |ΔPA| = 0.000 ≤ 0.03. Baseline greedy ổn định giữa 2 lần chạy.
- **Few-shot k=3 cải thiện PA rõ rệt**: -0.717 → -0.333 (đúng 1→5 câu, gấp 5 lần), nhưng chậm hơn hẳn (83.7s→134.5s/câu, prompt dài hơn do chèn ví dụ). Toàn bộ 30 câu bỏ qua đều do hết ngân sách 240s (budget-exhausted = abstained = 30), không phải model tự nhận không trả lời được.
- ⚠️ **Cảnh báo cho quyết định bật mặc định**: 2 lần đo này dùng `REASONING_AGENT_TIME_BUDGET=240` (dev), còn ngân sách nộp bài thật chỉ 45s. Few-shot làm mỗi câu tốn thêm thời gian xử lý prompt — ở ngân sách 45s rất hẹp, few-shot có thể khiến NHIỀU câu hết ngân sách hơn (PA giảm, không tăng) so với kết quả đo ở đây. Cần đo lại few-shot với ngân sách gần 45s (hoặc đo "thời gian tới token đầu tiên có thể trả lời" riêng) trước khi quyết định bật mặc định lúc nộp bài.
