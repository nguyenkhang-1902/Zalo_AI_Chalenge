# Runbook — QLoRA fine-tune student trên Kaggle (feature 008)

Chạy `scripts/kaggle_qlora.py` trên **Kaggle Notebook GPU free** (T4×2, 30h/tuần). Máy dev KHÔNG
chạy (RTX 3050 6GB + không có deps). Student: **Qwen2.5-Coder-7B-Instruct**.

## 0. Chuẩn bị dataset (ở máy dev, trước khi lên Kaggle)

> ⚠️ Sau khi `git pull`: `build_output/` bị gitignore (KHÔNG có trong repo) → PHẢI build lại train.
> Cần `train/` đã giải nén (BTC cấp, cũng gitignore). Mọi lệnh chạy ở gốc repo, có `PYTHONPATH=src`.

```bash
# 0) Build 30 business train (~2 phút) → *.duckdb + *.schema.json + rulebook.md + calendar.csv
PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m data_loader.build_all \
  --dataset-dir train --out build_output/train008

# 1) VALIDATE trước (quan trọng): --limit 50 để xác nhận gateway + model CÓ tool-calling + đo yield
TEACHER_MODEL=<model-có-tool-calling> TEACHER_BASE_URL=<gateway>/v1 TEACHER_API_KEY=<key> \
REASONING_AGENT_TIME_BUDGET=300 PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m distill.generate \
  --questions train/questions.jsonl --answers train/answers.jsonl \
  --dataset-dir build_output/train008 --out build_output/traces_probe.jsonl --limit 50
# → đếm status=verified trong traces_probe.jsonl. 0 verified mà model vẫn trả tool_calls → nhiều khả
#   năng model KHÔNG hỗ trợ function-calling (đổi model). Yield ổn thì chạy full:

# 2) Sinh trace verified toàn bộ train/ (tự loại DevSet; resume được nếu đứt giữa chừng)
TEACHER_MODEL=<model> TEACHER_BASE_URL=<gateway>/v1 TEACHER_API_KEY=<key> \
REASONING_AGENT_TIME_BUDGET=300 PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m distill.generate \
  --questions train/questions.jsonl --answers train/answers.jsonl \
  --dataset-dir build_output/train008 --out build_output/traces.jsonl --limit 0

# 3) Dựng SFT JSONL (loại DevSet, dedupe)
PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m distill.build_dataset \
  --traces build_output/traces.jsonl --questions train/questions.jsonl \
  --answers train/answers.jsonl --out build_output/sft.jsonl
```

**Tinh chỉnh cho gateway free (quan trọng):**
- `REASONING_AGENT_TIME_BUDGET=300` (đã có ở lệnh trên): teacher qua API lớn chậm hơn local; mặc
  định 45s hay bị cắt giữa chừng → yield verify thấp oan. Đặt cao cho data-gen (inference nộp bài
  vẫn 45s, không ảnh hưởng).
- Nếu gateway có **RPM limit** (vd Groq free ~30 req/phút) → thêm `DISTILL_SLEEP_SECONDS=2` (hoặc
  `--sleep-seconds 2`) vào lệnh generate để nghỉ giữa câu, tránh 429.
- **Câu lỗi tạm thời** (429/timeout) bị ghi `status:"failed"` kèm `error` và **bị bỏ qua khi
  resume**. Muốn thử lại nhóm này: lọc bỏ các dòng `"status":"failed"` khỏi `traces.jsonl` rồi chạy
  lại `distill.generate` (nó resume các id chưa có). Câu khó thật sẽ lại failed — đó là bình thường.

Upload `build_output/sft.jsonl` + `scripts/kaggle_qlora.py` làm Kaggle Dataset/Notebook input.

## 1. Cell cài deps (CHỈ trên Kaggle — không thêm vào requirements.txt)

```bash
pip install -q "unsloth[kaggle-new]" "trl>=0.12" "datasets"
```

## 2. Smoke run (BẮT BUỘC trước khi train thật)

```bash
python kaggle_qlora.py --data /kaggle/input/<ds>/sft.jsonl --out /kaggle/working/adapter --smoke
```

Mục tiêu smoke: xác nhận **chat template render đúng** `tool_calls` + `tool` role + `tools=` (đây là
điểm rủi ro đã flag ở spec). Nếu `apply_chat_template`/`train_on_responses_only` báo lỗi marker →
chỉnh `instruction_part`/`response_part` trong `kaggle_qlora.py` cho khớp template Qwen2.5 bản đang
dùng, chạy lại smoke. Ghi kết quả smoke (OK/lỗi + chỉnh gì) vào CUỐI file này.

## 3. Train thật

```bash
python kaggle_qlora.py --data /kaggle/input/<ds>/sft.jsonl --out /kaggle/working/adapter --epochs 1
```

Ghi lại: thời gian train, VRAM đỉnh, loss cuối (SC-004 cần số tái lập). Download `/kaggle/working/adapter`.

## 4. Serve để đo PA (vLLM, OpenAI endpoint)

```bash
pip install -q vllm
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-7B-Instruct --enable-lora \
  --lora-modules tuned=/kaggle/working/adapter --port 8000 --enable-auto-tool-choice --tool-call-parser hermes
```

Rồi đo baseline vs fine-tuned (reuse 007, xem `distill-finetune-tasks.md` Task 7 Step 6):

```bash
# baseline
REASONING_AGENT_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct REASONING_AGENT_BASE_URL=http://localhost:8000/v1 \
PYTHONIOENCODING=utf-8 python -m accuracy_boost.measure collect --dataset-dir <built train> --out runs_base.jsonl --limit 200
# fine-tuned (LoRA)
REASONING_AGENT_MODEL=tuned REASONING_AGENT_BASE_URL=http://localhost:8000/v1 \
PYTHONIOENCODING=utf-8 python -m accuracy_boost.measure collect --dataset-dir <built train> --out runs_tuned.jsonl --limit 200
# PA + phân loại lỗi
python -m accuracy_boost.measure report --runs runs_tuned.jsonl
# (+ distill.error_analysis.classify_outcomes để so wrong_VALUE trước/sau — SC-003)
```

## 5. Tuân thủ BTC (model card — rule 8.2 / 8.9)

- **Base**: `Qwen/Qwen2.5-Coder-7B-Instruct` · **license Apache-2.0** · phát hành **09/2024**
  (< 26/10/2026 ✓) · 7.6B params + **LoRA r=16** → tổng **< 15B** (rule 8.2 ✓).
- **Khai báo trong README solution**: tên base + commit/revision, LoRA adapter, tổng params inference.
- **Offline**: adapter + base nạp từ image/volume; teacher (API ngoài) KHÔNG có trong Docker (rule 8.3).
- **Gửi BTC verify** (rule 8.9.1/8.9.3): `build_output/sft.jsonl` (data train) + `scripts/kaggle_qlora.py`
  (code train) + `src/distill/` (code sinh data) + runbook này → `aichallenge@zalo.me`.
- **Tất định inference** (rule 8.8): serve temp 0 + seed cố định; kiểm `|ΔPA| ≤ 0.03` khi re-run (SC-007).

---

## Kết quả smoke / train (điền khi chạy)

> _(chưa chạy — điền sau khi smoke trên Kaggle: template OK?, chỉnh gì, thời gian train, VRAM, loss)_
