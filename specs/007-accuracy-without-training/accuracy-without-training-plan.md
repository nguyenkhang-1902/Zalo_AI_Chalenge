# Accuracy Without Training (007) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans để thực thi plan này theo từng task. Tasks chi tiết:
> `specs/007-accuracy-without-training/accuracy-without-training-tasks.md` (steps dùng checkbox).

**Goal:** Nâng điểm PA của pipeline `004`+`005` mà không train/fine-tune: cổng tin cậy (abstain),
semantic-layer tool, few-shot từ `train/`, và đo model 14B-Q4 — mỗi đòn bẩy đo A/B trên cùng bộ dev.

**Architecture:** Giữ nguyên `answer_question` (004) làm lõi; thêm `AgentOptions` (temperature, seed,
bật semantic tool, hook few-shot) để biến thể hoá 1 lần chạy mà không sửa hành vi mặc định. Package
mới `src/accuracy_boost/` chứa phần ngoài lõi: `consensus` (bỏ phiếu + đường cong PA), `gated`
(chạy N lần → đáp án hoặc `abstain`), `devset`/`measure` (bộ dev cố định + thu kết quả N lần có
resume + báo cáo PA theo ngưỡng), `fewshot` (pool từ `train/`). Semantic tool nằm trong
`reasoning_agent/semantic_tools.py` vì là tool của vòng ReAct. `005` runner được sửa nhỏ để không
ghi dòng `abstain` vào `submission.jsonl` (thiếu dòng = 0 điểm theo BTC).

**Tech Stack:** Python 3.11, DuckDB, pytest, stdlib (không thêm dependency; Điều 1/8).

## Global Constraints

- Không logic rẽ nhánh theo `business_id`/`question_id` hay tên cột cụ thể (FR-008, Điều 10).
- Không dùng `public_test`/`private_test` cho few-shot, chọn ngưỡng, tinh chỉnh prompt (FR-009,
  rule 8.9.2). Mọi phép đo chỉ trên `train/`.
- Ngưỡng/N/seed/k đọc từ config/env, không magic value (Điều 4).
- Tên model/endpoint chỉ qua `REASONING_AGENT_MODEL`/`REASONING_AGENT_BASE_URL` (FR-006, SC-005).
- Tất định: seed theo chỉ số lần chạy (`seed_i = base_seed + i`), không theo `question_id` (FR-010).
- Hành vi mặc định của `answer_question` KHÔNG đổi khi không truyền `options` (test 004 giữ nguyên).
- File Python `snake_case`, tách khi > ~250 dòng (Điều 5); tên cột tiếng Việt giữ nguyên (Điều 3).
- Không tự tải model nặng/cài lib (CLAUDE.md) — Task 6 có cổng hỏi Khang trước khi tải 14B.
- Commit message Conventional Commits tiếng Anh; không tự `git push`.

## Quyết định thiết kế bổ sung (lúc viết plan)

- **Run 0 luôn greedy** (temperature 0, seed = base), các run sau `temperature = 0.7`, `seed =
  base + i`. Đáp án cuối khi đồng thuận = đáp án của run đầu tiên khớp nhóm thắng.
- **Kết quả "hết ngân sách" (FR-005 của 004) coi là phiếu abstain**, không phải phiếu
  `unanswerable`: với PA, trả `unanswerable` sai tốn −1 trong ~98% câu. Phiếu abstain không bao giờ
  thắng; chỉ ghi nhận làm giảm độ đồng thuận.
- **US1 AC3 (tín hiệu từ kết quả SQL rỗng/NULL) HOÃN** (YAGNI): react_loop hiện chỉ trả đáp án
  cuối, không lộ lịch sử tool; chỉ làm nếu số đo Task 6 cho thấy đồng thuận một mình chưa đủ.
- **Dòng `abstain` không ghi vào `submission.jsonl`** (thiếu dòng = 0 điểm, chắc chắn đúng theo
  slide chấm điểm); định dạng `abstain` tường minh chờ Docker guideline. Hệ quả: resume sẽ chạy lại
  câu abstain (chấp nhận).
- **Few-shot chỉ truyền `type` của câu tương tự**, không truyền giá trị đáp án/SQL (train chỉ có
  đáp án, khác business → giá trị đáp án dễ gây nhiễu). Độ giống = Jaccard token (bỏ dấu), không cần
  embedding/thư viện mới.
- **Semantic tool** chỉ sinh SQL từ tham số đã kiểm với `schema.json` (tên bảng/cột + `?` bind cho
  giá trị); mọi định nghĩa nghiệp vụ (trạng thái loại trừ, loại giao dịch) do model chọn từ rulebook.
  Có `tie_break_column` vì rulebook §"Bằng nhau" xếp theo mã tăng dần.
- **Rủi ro quan sát được**: `react_loop` dùng `json.dumps(result)` không `default=` → kết quả có
  `Decimal`/`date` từ DuckDB làm vòng lặp nổ. Task 1 sửa bằng `default=str`.
- **Thời gian đo**: máy dev 6GB GPU chậm; Task 6 bắt đầu bằng `--limit 60` rồi mới mở rộng 200.
