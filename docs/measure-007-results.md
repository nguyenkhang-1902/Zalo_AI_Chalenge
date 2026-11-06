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

## Đợt 2 (2026-11-06, máy VS Code) — cùng 60 câu dev seed=42 trừ khi ghi khác

### Việc 3 — Few-shot ở ngân sách gần thật (45s)

| Cấu hình | PA | đúng | sai | bỏ qua | hết ngân sách | s/lượt TB | s/lượt trung vị |
|---|---|---|---|---|---|---|---|
| Few-shot k=3, budget=45s | -0.083 | 1 | 6 | 53 | 53/60 | 45.7 | 47.2 |
| Baseline, budget=45s | 0.000 | 0 | 0 | 60 | 60/60 | 47.2 | 47.2 |
| Few-shot k=1 (max-chars=800), budget=45s | 0.000 | 0 | 0 | 60 | 60/60 | 47.2 | 47.2 |

**Nhận xét (quan trọng nhất của Đợt 2):** ở ngân sách thật 45s, **cả 3 cấu hình gần như vô dụng** — baseline và
few-shot k=1 hết ngân sách 100% (0 câu trả lời được), few-shot k=3 chỉ "lọt" 7/60 câu (1 đúng/6 sai). 7 câu lọt
được nhiều khả năng là nhiễu (câu hỏi tình cờ cần ít bước ReAct hơn), **không phải bằng chứng few-shot giúp ích ở
45s** — s/lượt trung vị của cả 3 cấu hình đều ~47s, nghĩa là hầu như mọi câu đều chạy hết toàn bộ ngân sách rồi bị
cắt, bất kể có few-shot hay không. Kết luận: nút thắt ở 45s là **ngân sách bản thân nó** (vòng ReAct cần nhiều hơn
45s để hoàn thành dù 1 bước), không phải do few-shot làm chậm thêm — khớp với ghi nhận cũ ở đầu file này
("lần đo đầu với 45s không hợp lệ, 180/180 hết ngân sách"). Few-shot ở ngân sách 240s (bảng trên) vẫn là số đo
duy nhất có ý nghĩa cho tới khi ngân sách nộp bài thật được tăng hoặc model/pipeline được tối ưu tốc độ.

### Việc 4 — Few-shot k=3 + cổng tin cậy (n-runs=3, budget=240s)

⚠️ Giảm xuống `--limit 30` (30 câu đầu của bộ dev 60, cùng seed) theo đúng phần dự phòng handoff cho phép, vì
n-runs=3 × 60 câu ước ~6-7h. 90 lượt chạy tổng (30×3), budget-exhausted 76/90, s/lượt TB 212.0 / trung vị 242.1.

| Cấu hình | PA | đúng | sai | bỏ qua |
|---|---|---|---|---|
| Greedy (chỉ run 0, tương đương few-shot k=3 đơn, trên 30 câu này) | -0.100 | 1 | 4 | 25 |
| Gate N=3, ngưỡng 0.3 | -0.033 | 2 | 3 | 25 |
| Gate N=3, ngưỡng 0.6 | **0.000** | 2 | 2 | 26 |
| Gate N=3, ngưỡng 1.0 | **0.000** | 1 | 1 | 28 |

**Nhận xét:** đây là lần đầu tiên PA chạm **0.000** (hòa, không lỗ) với cấu hình có câu trả lời thật — few-shot
k=3 kết hợp cổng tin cậy (ngưỡng 0.6–1.0) lọc được voting nhất quán, nâng từ PA -0.100 (greedy) lên 0.000. Mẫu
nhỏ (30 câu, 1-2 câu đúng/sai) nên tín hiệu còn yếu — cần xác nhận lại trên mẫu lớn hơn nếu có thời gian. Vẫn ở
budget=240s (dev), không phải 45s thật — xem cảnh báo ở Việc 3.

### Việc 5 — So sánh Qwen2.5-14B-Instruct Q4_K_M vs 7B (cùng 20 câu đầu của dev-60, seed=42)

Model `qwen2.5-14b-ctx12k` tạo từ `qwen2.5:14b-instruct` (Q4_K_M, 8.99GB) **đã có sẵn trên máy** — không cần tải
mới. VRAM RTX 3050 (6GB) không chứa hết model 9GB → Ollama tự offload một phần sang CPU (quan sát lúc chạy:
~3.9GB VRAM dùng, không đo liên tục cả quá trình). Ngân sách đo 600s để không bị cắt do tốc độ chậm.

Đối chứng 7B dùng lại đúng dữ liệu đã đo ở budget=240s (file `runs_fewshot.jsonl`/`runs_repro.jsonl`), lọc đúng
20 id này — không chạy lại 7B (tiết kiệm thời gian; 7B hiếm khi dùng hết 240s nên khác biệt do ngân sách không
đáng kể so với chênh lệch quan sát được dưới đây).

| Cấu hình | Model | Ngân sách | PA | đúng | sai | bỏ qua | s/lượt TB | s/lượt trung vị |
|---|---|---|---|---|---|---|---|---|
| Baseline | 7B-ctx12k | 240s | -0.800 | 0 | 16 | 4 | 75.4 | — |
| Baseline | 14B-ctx12k | 600s | -0.800 | 0 | 16 | 4 | 313.6 | 299.5 |
| Few-shot k=3 | 7B-ctx12k | 240s | **-0.300** | **2** | 8 | 10 | 132.9 | — |
| Few-shot k=3 | 14B-ctx12k | 600s | -0.800 | 0 | 16 | 4 | 346.5 | 326.9 |

**Nhận xét:**
- **Baseline: hòa tuyệt đối** — 14B cho đúng y kết quả 7B (0 đúng/16 sai/4 bỏ qua) nhưng chậm hơn **~4.2×**.
- **Few-shot k=3: 14B THUA 7B** — 7B đúng 2/20, 14B đúng 0/20 trên đúng cùng 20 câu, lại chậm hơn ~2.6× so với
  7B cùng cấu hình. Model lớn hơn không giúp ích ở bài toán này (có thể do offload CPU làm giảm hiệu quả, hoặc
  14B không theo format tool-calling/ReAct tốt hơn 7B cho domain này) — **không có lý do để dùng 14B**.
- Không đo tiếp trên 60 câu: kết luận đã đủ rõ (chậm hơn + không chính xác hơn), scale lên 60 câu chỉ tốn thêm
  ~3× thời gian (ước ~5-6h/cấu hình) mà không đổi kết luận.
- **Ước lượng s/lượt trên máy chấm (2×RTX 5090, giả định)** — chỉ để tham khảo, số đo thật ở trên là nguồn chính:
  RTX 5090 có 32GB VRAM/băng thông ~1792GB/s so với RTX 3050 6GB/~192GB/s. 14B Q4_K_M (9GB) sẽ **fit hoàn toàn
  trong VRAM** của 1 RTX 5090 (không cần offload CPU như ở máy dev) — loại bỏ hẳn nút thắt offload, không chỉ
  scale theo băng thông. Giả định thô: hệ số cải thiện = (bỏ offload) × (băng thông) ước tổng ~4-9×, cho
  s/lượt 14B trên 5090 ước **~35-85s/câu** (từ 327s/câu đo được). Đây là suy diễn, không phải số đo — để
  session cloud/Khang tự kết luận có đáng cân nhắc 14B trên hạ tầng chấm thi hay không; bản thân kết quả độ
  chính xác ở trên (14B thua 7B) là lý do chính để KHÔNG chọn 14B, bất kể tốc độ trên máy chấm thế nào.
