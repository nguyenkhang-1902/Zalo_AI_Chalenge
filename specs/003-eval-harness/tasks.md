# Tasks: Eval Harness

> REQUIRED SUB-SKILL khi thực thi: `superpowers:subagent-driven-development` (khuyến nghị) hoặc
> `superpowers:executing-plans`. Mỗi task kết thúc bằng bước chạy test thật, không coi "xong" khi
> chưa thấy PASS.

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Global Constraints (áp dụng mọi task)

- Không `business_id`/`question_id` cụ thể nào trong logic rẽ nhánh (rule 4 cuộc thi) — chỉ dùng
  trong test/golden test.
- Chỉ dùng stdlib (`json`, `re`, `argparse`, `dataclasses`) — không thêm dependency mới.
- Sai FORMAT hoặc sai GIÁ TRỊ hợp lệ (khác type, khác giá trị) → tính điểm -1, KHÔNG raise.
- Lỗi DỮ LIỆU thật (id trùng trong submission, `answers.jsonl` thiếu entry cho 1 id trong
  `questions.jsonl`) → MUST raise `ValueError`.
- `number`/`percent` so bằng epsilon nhỏ (`1e-6`), không so `==` tuyệt đối.
- Test liên quan dữ liệu thật MUST dùng trực tiếp `train/answers.jsonl`/`train/questions.jsonl`,
  không bịa dữ liệu khi có thể dùng ví dụ thật.
- Dùng lại venv + `requirements.txt`/`pytest.ini` đã có.

---

## Phase 1: Matchers — các type đơn giản

### Task 1: T001 [P] `matchers.py` phần A — number/percent/date/boolean/string

**Files:**
- Create: `src/eval_harness/__init__.py` (file rỗng — tạo ở task này để package import được, nội
  dung export đầy đủ thêm ở Task 5)
- Create: `src/eval_harness/matchers.py`
- Test: `tests/eval_harness/test_matchers.py`

**Interfaces:**
- Produces: `NUMBER_EPSILON: float`, `match_number(predicted, truth) -> bool`,
  `match_percent(predicted, truth) -> bool`, `match_date(predicted, truth) -> bool`,
  `match_boolean(predicted, truth) -> bool`, `match_string(predicted, truth, alias: list[str]) ->
  bool`. Task 2 thêm hàm vào CÙNG file này (không tạo lại). Task 5 import toàn bộ hàm public vào
  `__init__.py`.

- [ ] **Step 1: Viết test trước — dùng ví dụ thật từ `train/answers.jsonl`**

```python
# tests/eval_harness/test_matchers.py
from eval_harness.matchers import (
    match_boolean,
    match_date,
    match_number,
    match_percent,
    match_string,
)


def test_match_number_exact():
    assert match_number(89526400, 89526400) is True


def test_match_number_tolerates_float_epsilon():
    assert match_number(2954200.0000001, 2954200) is True


def test_match_number_rejects_wrong_value():
    assert match_number(89526400, 89526401) is False


def test_match_percent_exact():
    # q_00558c1410ef trong train/answers.jsonl thật: tỉ lệ huỷ đơn 6/2025 = 2.08%
    assert match_percent(2.08, 2.08) is True


def test_match_percent_rejects_wrong_value():
    assert match_percent(2.09, 2.08) is False


def test_match_date_exact_day():
    # q_046b75d6192e trong train/answers.jsonl thật
    assert match_date("2025-02-15", "2025-02-15") is True


def test_match_date_rejects_wrong_format():
    assert match_date("15/02/2025", "2025-02-15") is False


def test_match_boolean_exact():
    # q_0fc33ac2add7 trong train/answers.jsonl thật
    assert match_boolean(False, False) is True


def test_match_boolean_rejects_non_bool():
    assert match_boolean(0, False) is False  # 0 không phải bool, dù 0 == False trong Python


def test_match_string_exact():
    # q_06de33fa21cc trong train/answers.jsonl thật
    assert match_string(
        "Xi măng Hà Tiên PCB40 bao 50kg", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]
    ) is True


def test_match_string_case_whitespace_punctuation_insensitive():
    assert match_string(
        "  xi măng   hà tiên pcb40, bao 50kg.  ", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]
    ) is True


def test_match_string_accepts_alias_code():
    assert match_string("SP0001", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]) is True


def test_match_string_rejects_wrong_diacritics():
    # dấu tiếng Việt phải đúng — "mang" khác "măng"
    assert match_string(
        "Xi mang Hà Tiên PCB40 bao 50kg", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]
    ) is False


def test_match_string_rejects_unrelated_value():
    assert match_string("Gạch ống 8x8x18 Tuynel", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]) is False
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_matchers.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'eval_harness'`

- [ ] **Step 3: Tạo `src/eval_harness/__init__.py` rỗng**

```python
```

- [ ] **Step 4: Viết `src/eval_harness/matchers.py`**

```python
"""So khớp giá trị dự đoán với ground truth theo rulebook.md §9 — xem specs/003-eval-harness/spec.md."""
from __future__ import annotations

import re

NUMBER_EPSILON = 1e-6


def _normalize_string(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s


def match_number(predicted, truth) -> bool:
    if isinstance(predicted, bool) or isinstance(truth, bool):
        return False
    if not isinstance(predicted, (int, float)) or not isinstance(truth, (int, float)):
        return False
    return abs(predicted - truth) < NUMBER_EPSILON


def match_percent(predicted, truth) -> bool:
    return match_number(predicted, truth)


def match_date(predicted, truth) -> bool:
    return isinstance(predicted, str) and isinstance(truth, str) and predicted == truth


def match_boolean(predicted, truth) -> bool:
    return isinstance(predicted, bool) and isinstance(truth, bool) and predicted == truth


def match_string(predicted, truth: str, alias: list[str]) -> bool:
    if not isinstance(predicted, str):
        return False
    normalized_predicted = _normalize_string(predicted)
    candidates = [truth, *(alias or [])]
    return any(
        isinstance(c, str) and normalized_predicted == _normalize_string(c) for c in candidates
    )
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_matchers.py -v`
Expected: 14 passed

- [ ] **Step 6: Commit**

```bash
git add src/eval_harness/__init__.py src/eval_harness/matchers.py tests/eval_harness/test_matchers.py
git commit -m "feat(eval-harness): add number/percent/date/boolean/string matchers"
```

---

### Task 2: T002 `matchers.py` phần B — list/table/unanswerable + dispatcher

**Files:**
- Modify: `src/eval_harness/matchers.py` (thêm hàm vào file Task 1 đã tạo)
- Test: `tests/eval_harness/test_matchers.py` (thêm test vào file Task 1 đã tạo)

**Interfaces:**
- Consumes: `match_number`, `match_string` từ Task 1 (cùng file, gọi trực tiếp không cần import).
- Produces: `match_list(predicted, truth: list, alias: list[list]) -> bool`,
  `match_table(predicted, truth: dict, alias: list[list]) -> bool`,
  `match_unanswerable(predicted_type: str) -> bool`,
  `is_correct(truth_type: str, predicted: dict, truth_answer, alias: list) -> bool` (dispatcher
  theo `truth_type`, dùng bởi Task 4's `scoring.py`).

- [ ] **Step 1: Viết test trước — dùng ví dụ thật từ `train/answers.jsonl`**

```python
# thêm vào cuối tests/eval_harness/test_matchers.py
from eval_harness.matchers import is_correct, match_list, match_table, match_unanswerable


def test_match_list_exact_with_alias_codes():
    # q_019ec94d9799 trong train/answers.jsonl thật
    truth = ["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"]
    alias = [["SP0003"], ["SP0017"], ["SP0001"]]
    assert match_list(["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"], truth, alias) is True


def test_match_list_accepts_alias_per_position():
    truth = ["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"]
    alias = [["SP0003"], ["SP0017"], ["SP0001"]]
    assert match_list(["SP0003", "SP0017", "SP0001"], truth, alias) is True


def test_match_list_rejects_wrong_order():
    truth = ["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"]
    alias = [["SP0003"], ["SP0017"], ["SP0001"]]
    assert match_list(["Trà đào cam sả (M)", "Cà phê sữa (M)", "Cà phê đen (M)"], truth, alias) is False


def test_match_list_rejects_wrong_length():
    truth = ["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"]
    assert match_list(["Cà phê sữa (M)", "Trà đào cam sả (M)"], truth, [[], [], []]) is False


def test_match_list_of_numbers():
    assert match_list([287435200, 346554700, 309693800], [287435200, 346554700, 309693800], [[], [], []]) is True


TABLE_TRUTH = {
    "columns": ["khach_hang", "so_tien_no"],
    "rows": [
        ["Đỗ Đức An", 404500],
        ["Dương Tâm Bích", 158600],
        ["Phùng Hồng Nam", 126000],
    ],
}
TABLE_ALIAS = [["KH0124"], ["KH0233"], ["KH0137"]]


def test_match_table_exact_same_order():
    predicted = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [
            ["Đỗ Đức An", 404500],
            ["Dương Tâm Bích", 158600],
            ["Phùng Hồng Nam", 126000],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is True


def test_match_table_row_order_does_not_matter():
    predicted = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [
            ["Phùng Hồng Nam", 126000],
            ["Đỗ Đức An", 404500],
            ["Dương Tâm Bích", 158600],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is True


def test_match_table_accepts_alias_code_as_row_key():
    predicted = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [
            ["KH0124", 404500],
            ["KH0233", 158600],
            ["KH0137", 126000],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is True


def test_match_table_column_order_independent_when_names_match():
    predicted = {
        "columns": ["so_tien_no", "khach_hang"],
        "rows": [
            [404500, "Đỗ Đức An"],
            [158600, "Dương Tâm Bích"],
            [126000, "Phùng Hồng Nam"],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is True


def test_match_table_rejects_wrong_value():
    predicted = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [
            ["Đỗ Đức An", 999999],
            ["Dương Tâm Bích", 158600],
            ["Phùng Hồng Nam", 126000],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is False


def test_match_unanswerable_ignores_reason_content():
    assert match_unanswerable("unanswerable") is True
    assert match_unanswerable("number") is False


def test_is_correct_dispatches_by_type():
    assert is_correct("number", {"type": "number", "answer": 89526400}, 89526400, []) is True
    assert is_correct("number", {"type": "string", "answer": "x"}, 89526400, []) is False
    assert is_correct("unanswerable", {"type": "unanswerable", "reason": "..."}, None, []) is True
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_matchers.py -v`
Expected: FAIL với `ImportError: cannot import name 'match_list' from 'eval_harness.matchers'`

- [ ] **Step 3: Thêm vào cuối `src/eval_harness/matchers.py`**

```python
def match_list(predicted, truth: list, alias: list) -> bool:
    if not isinstance(predicted, list) or len(predicted) != len(truth):
        return False
    alias = alias or [[] for _ in truth]
    for i, truth_val in enumerate(truth):
        pred_val = predicted[i]
        elem_alias = alias[i] if i < len(alias) else []
        if isinstance(truth_val, str):
            if not match_string(pred_val, truth_val, elem_alias):
                return False
        elif isinstance(truth_val, (int, float)) and not isinstance(truth_val, bool):
            if not match_number(pred_val, truth_val):
                return False
        else:
            if pred_val != truth_val:
                return False
    return True


def _column_index_map(pred_columns: list, truth_columns: list) -> list | None:
    if len(pred_columns) == len(truth_columns) and set(pred_columns) == set(truth_columns):
        return [pred_columns.index(c) for c in truth_columns]
    return None


def _row_matches(pred_row: list, truth_row: list, row_alias: list) -> bool:
    if not match_string(pred_row[0], truth_row[0], row_alias):
        return False
    for i in range(1, len(truth_row)):
        if not match_number(pred_row[i], truth_row[i]):
            return False
    return True


def match_table(predicted, truth: dict, alias: list) -> bool:
    if not isinstance(predicted, dict):
        return False
    pred_columns = predicted.get("columns")
    pred_rows = predicted.get("rows")
    if not isinstance(pred_columns, list) or not isinstance(pred_rows, list):
        return False

    truth_columns = truth["columns"]
    truth_rows = truth["rows"]
    if len(pred_columns) != len(truth_columns) or len(pred_rows) != len(truth_rows):
        return False

    index_map = _column_index_map(pred_columns, truth_columns)
    if index_map is None:
        index_map = list(range(len(truth_columns)))

    reordered_pred_rows = []
    for row in pred_rows:
        if not isinstance(row, list) or len(row) != len(truth_columns):
            return False
        reordered_pred_rows.append([row[i] for i in index_map])

    alias = alias or [[] for _ in truth_rows]
    used = [False] * len(reordered_pred_rows)
    for t_idx, truth_row in enumerate(truth_rows):
        row_alias = alias[t_idx] if t_idx < len(alias) else []
        matched = False
        for p_idx, pred_row in enumerate(reordered_pred_rows):
            if used[p_idx]:
                continue
            if _row_matches(pred_row, truth_row, row_alias):
                used[p_idx] = True
                matched = True
                break
        if not matched:
            return False
    return True


def match_unanswerable(predicted_type: str) -> bool:
    return predicted_type == "unanswerable"


def is_correct(truth_type: str, predicted: dict, truth_answer, alias: list) -> bool:
    if predicted.get("type") != truth_type:
        return False
    if truth_type == "unanswerable":
        return True

    predicted_answer = predicted.get("answer")
    if truth_type == "number":
        return match_number(predicted_answer, truth_answer)
    if truth_type == "percent":
        return match_percent(predicted_answer, truth_answer)
    if truth_type == "date":
        return match_date(predicted_answer, truth_answer)
    if truth_type == "boolean":
        return match_boolean(predicted_answer, truth_answer)
    if truth_type == "string":
        return match_string(predicted_answer, truth_answer, alias)
    if truth_type == "list":
        return match_list(predicted_answer, truth_answer, alias)
    if truth_type == "table":
        return match_table(predicted_answer, truth_answer, alias)
    return False
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_matchers.py -v`
Expected: 26 passed (14 cũ + 12 mới)

- [ ] **Step 5: Commit**

```bash
git add src/eval_harness/matchers.py tests/eval_harness/test_matchers.py
git commit -m "feat(eval-harness): add list/table/unanswerable matchers and is_correct dispatcher"
```

---

## Phase 2: Report structure

### Task 3: T003 `report.py` — TypeBreakdown/EvalReport/format_report

**Files:**
- Create: `src/eval_harness/report.py`
- Test: `tests/eval_harness/test_report.py`

**Interfaces:**
- Produces: `TypeBreakdown` (dataclass: `correct: int = 0, incorrect: int = 0, abstained: int = 0`,
  method `record(outcome: str) -> None`, property `total -> int`, property `accuracy -> float`),
  `EvalReport` (dataclass: `total_score: int, total_questions: int, correct: int, incorrect: int,
  abstained: int, accuracy: float, by_type: dict[str, TypeBreakdown], by_business: dict[str,
  TypeBreakdown], malformed_count: int, extra_ids_ignored: int`), `format_report(report:
  EvalReport) -> str`. Task 4's `scoring.py` tạo ra các object này; Task 5 import vào
  `__init__.py`.

- [ ] **Step 1: Viết test trước**

```python
# tests/eval_harness/test_report.py
from eval_harness.report import EvalReport, TypeBreakdown, format_report


def test_type_breakdown_records_outcomes():
    bd = TypeBreakdown()
    bd.record("correct")
    bd.record("correct")
    bd.record("incorrect")
    bd.record("abstained")
    assert bd.correct == 2
    assert bd.incorrect == 1
    assert bd.abstained == 1
    assert bd.total == 4
    assert bd.accuracy == 0.5


def test_type_breakdown_accuracy_zero_when_empty():
    bd = TypeBreakdown()
    assert bd.total == 0
    assert bd.accuracy == 0.0


def test_format_report_includes_totals_and_breakdowns():
    by_type = {"number": TypeBreakdown(correct=1, incorrect=0, abstained=0)}
    by_business = {"biz_001": TypeBreakdown(correct=1, incorrect=0, abstained=0)}
    report = EvalReport(
        total_score=1,
        total_questions=1,
        correct=1,
        incorrect=0,
        abstained=0,
        accuracy=1.0,
        by_type=by_type,
        by_business=by_business,
        malformed_count=0,
        extra_ids_ignored=0,
    )
    text = format_report(report)
    assert "Tổng điểm: 1 / 1" in text
    assert "number" in text
    assert "biz_001" in text
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_report.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'eval_harness.report'`

- [ ] **Step 3: Viết `src/eval_harness/report.py`**

```python
"""Cấu trúc kết quả chấm điểm — xem specs/003-eval-harness/spec.md."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TypeBreakdown:
    correct: int = 0
    incorrect: int = 0
    abstained: int = 0

    def record(self, outcome: str) -> None:
        if outcome == "correct":
            self.correct += 1
        elif outcome == "incorrect":
            self.incorrect += 1
        else:
            self.abstained += 1

    @property
    def total(self) -> int:
        return self.correct + self.incorrect + self.abstained

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass
class EvalReport:
    total_score: int
    total_questions: int
    correct: int
    incorrect: int
    abstained: int
    accuracy: float
    by_type: dict = field(default_factory=dict)
    by_business: dict = field(default_factory=dict)
    malformed_count: int = 0
    extra_ids_ignored: int = 0


def format_report(report: EvalReport) -> str:
    lines = [
        f"Tổng điểm: {report.total_score} / {report.total_questions}",
        f"Đúng: {report.correct}  Sai: {report.incorrect}  Bỏ trống: {report.abstained}",
        f"Accuracy: {report.accuracy:.4f}",
        f"Dòng hỏng: {report.malformed_count}  Id lạ bị bỏ qua: {report.extra_ids_ignored}",
        "",
        "Theo type:",
    ]
    for type_name, bd in sorted(report.by_type.items()):
        lines.append(f"  {type_name}: {bd.correct}/{bd.total} ({bd.accuracy:.2%})")
    lines.append("")
    lines.append("Theo business:")
    for business_id, bd in sorted(report.by_business.items()):
        lines.append(f"  {business_id}: {bd.correct}/{bd.total} ({bd.accuracy:.2%})")
    return "\n".join(lines)
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_report.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/eval_harness/report.py tests/eval_harness/test_report.py
git commit -m "feat(eval-harness): add TypeBreakdown/EvalReport and format_report"
```

---

## Phase 3: Scoring orchestration

### Task 4: T004 `scoring.py` — đọc file + chấm điểm toàn bộ

**Files:**
- Create: `src/eval_harness/scoring.py`
- Test: `tests/eval_harness/test_scoring_golden.py`

**Interfaces:**
- Consumes: `is_correct` từ `src/eval_harness/matchers.py` (Task 2); `TypeBreakdown`, `EvalReport`
  từ `src/eval_harness/report.py` (Task 3).
- Produces: `score_submission(questions_path: str, answers_path: str, submission_path: str) ->
  EvalReport`. Task 5's `cli.py` gọi hàm này.

- [ ] **Step 1: Viết test trước — dùng TOÀN BỘ `train/` thật (3000 câu) + các case lỗi**

```python
# tests/eval_harness/test_scoring_golden.py
import json
from pathlib import Path

import pytest

from eval_harness.scoring import score_submission

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAIN_QUESTIONS = REPO_ROOT / "train" / "questions.jsonl"
TRAIN_ANSWERS = REPO_ROOT / "train" / "answers.jsonl"


def _write_submission(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_answers_as_submission_rows() -> list[dict]:
    rows = []
    with open(TRAIN_ANSWERS, encoding="utf-8") as f:
        for line in f:
            a = json.loads(line)
            rows.append({"id": a["id"], "type": a["type"], "answer": a["answer"]})
    return rows


def test_perfect_submission_scores_100_percent_on_real_train_set(tmp_path):
    rows = _load_answers_as_submission_rows()
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.total_questions == 3000
    assert report.correct == 3000
    assert report.incorrect == 0
    assert report.abstained == 0
    assert report.accuracy == 1.0
    assert report.total_score == 3000


def test_wrong_submission_loses_2_points_per_wrong_question(tmp_path):
    rows = _load_answers_as_submission_rows()
    # Sửa sai 5 câu number đầu tiên: cộng thêm 1 vào giá trị đúng
    wrong_count = 0
    for row in rows:
        if row["type"] == "number" and wrong_count < 5:
            row["answer"] = row["answer"] + 1
            wrong_count += 1
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.incorrect == 5
    assert report.correct == 2995
    assert report.total_score == 3000 - 2 * 5


def test_missing_id_in_submission_scores_zero_not_negative(tmp_path):
    rows = _load_answers_as_submission_rows()[3:]  # bỏ qua 3 câu đầu
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.abstained == 3
    assert report.correct == 2997
    assert report.total_score == 2997


def test_explicit_abstain_scores_zero(tmp_path):
    rows = _load_answers_as_submission_rows()
    rows[0] = {"id": rows[0]["id"], "type": "abstain"}
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.abstained == 1
    assert report.correct == 2999


def test_malformed_json_line_scores_zero_without_crashing(tmp_path):
    rows = _load_answers_as_submission_rows()
    submission_path = tmp_path / "submission.jsonl"
    with open(submission_path, "w", encoding="utf-8") as f:
        f.write("{not valid json\n")
        for row in rows[1:]:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert report.malformed_count == 1
    assert report.abstained == 1
    assert report.correct == 2999


def test_duplicate_id_in_submission_raises_value_error(tmp_path):
    rows = _load_answers_as_submission_rows()[:2]
    rows.append(rows[0])  # id trùng
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    with pytest.raises(ValueError):
        score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))


def test_breakdown_by_type_and_business_sum_to_total(tmp_path):
    rows = _load_answers_as_submission_rows()
    submission_path = tmp_path / "submission.jsonl"
    _write_submission(submission_path, rows)

    report = score_submission(str(TRAIN_QUESTIONS), str(TRAIN_ANSWERS), str(submission_path))

    assert sum(bd.total for bd in report.by_type.values()) == 3000
    assert sum(bd.total for bd in report.by_business.values()) == 3000
    assert set(report.by_type.keys()) == {
        "number", "percent", "date", "boolean", "string", "list", "table", "unanswerable",
    }


def test_answers_missing_entry_for_question_raises_value_error(tmp_path):
    questions_path = tmp_path / "questions.jsonl"
    answers_path = tmp_path / "answers.jsonl"
    submission_path = tmp_path / "submission.jsonl"

    with open(questions_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"id": "q_x", "business_id": "biz_x", "question": "?", "as_of_date": "2026-01-01"}) + "\n")
    with open(answers_path, "w", encoding="utf-8") as f:
        pass  # rỗng — thiếu entry cho q_x
    with open(submission_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"id": "q_x", "type": "number", "answer": 1}) + "\n")

    with pytest.raises(ValueError):
        score_submission(str(questions_path), str(answers_path), str(submission_path))
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_scoring_golden.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'eval_harness.scoring'`

- [ ] **Step 3: Viết `src/eval_harness/scoring.py`**

```python
"""Đọc questions/answers/submission và chấm điểm — xem specs/003-eval-harness/spec.md."""
from __future__ import annotations

import json

from .matchers import is_correct
from .report import EvalReport, TypeBreakdown


def _load_jsonl(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_submission(path: str) -> tuple[dict, int]:
    submission: dict = {}
    malformed_count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                malformed_count += 1
                continue
            row_id = row.get("id")
            if not isinstance(row_id, str):
                malformed_count += 1
                continue
            if row_id in submission:
                raise ValueError(f"id trùng lặp trong submission: {row_id}")
            submission[row_id] = row
    return submission, malformed_count


def score_submission(questions_path: str, answers_path: str, submission_path: str) -> EvalReport:
    questions = _load_jsonl(questions_path)
    answers = _load_jsonl(answers_path)
    submission, malformed_count = _load_submission(submission_path)

    answers_by_id = {a["id"]: a for a in answers}
    for q in questions:
        if q["id"] not in answers_by_id:
            raise ValueError(f"answers.jsonl thiếu entry cho id: {q['id']}")

    extra_ids_ignored = sum(1 for sid in submission if sid not in answers_by_id)

    by_type: dict = {}
    by_business: dict = {}
    total_score = 0
    correct = incorrect = abstained = 0

    for q in questions:
        qid = q["id"]
        truth = answers_by_id[qid]
        truth_type = truth["type"]
        business_id = q["business_id"]

        pred = submission.get(qid)
        if pred is None or pred.get("type") == "abstain":
            points = 0
            outcome = "abstained"
        elif is_correct(truth_type, pred, truth.get("answer"), truth.get("alias")):
            points = 1
            outcome = "correct"
        else:
            points = -1
            outcome = "incorrect"

        total_score += points
        if outcome == "correct":
            correct += 1
        elif outcome == "incorrect":
            incorrect += 1
        else:
            abstained += 1

        by_type.setdefault(truth_type, TypeBreakdown()).record(outcome)
        by_business.setdefault(business_id, TypeBreakdown()).record(outcome)

    total_questions = len(questions)
    accuracy = correct / total_questions if total_questions else 0.0

    return EvalReport(
        total_score=total_score,
        total_questions=total_questions,
        correct=correct,
        incorrect=incorrect,
        abstained=abstained,
        accuracy=accuracy,
        by_type=by_type,
        by_business=by_business,
        malformed_count=malformed_count,
        extra_ids_ignored=extra_ids_ignored,
    )
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_scoring_golden.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/eval_harness/scoring.py tests/eval_harness/test_scoring_golden.py
git commit -m "feat(eval-harness): add score_submission orchestrating real questions/answers/submission"
```

---

## Phase 4: Package exports + CLI

### Task 5: T005 `__init__.py` export + `cli.py`

**Files:**
- Modify: `src/eval_harness/__init__.py` (file rỗng từ Task 1, điền export ở đây)
- Create: `src/eval_harness/cli.py`
- Test: `tests/eval_harness/test_package_exports.py`

**Interfaces:**
- Consumes: `score_submission` (Task 4), `EvalReport`, `TypeBreakdown`, `format_report` (Task 3).
- Produces: `eval_harness` package — `004`/`005` import `score_submission`/`EvalReport` trực tiếp
  từ `eval_harness`; CLI `python -m eval_harness.cli --questions ... --answers ... --submission ...`.

- [ ] **Step 1: Viết test trước — import thẳng từ package root**

```python
# tests/eval_harness/test_package_exports.py
def test_all_public_symbols_importable_from_package_root():
    from eval_harness import EvalReport, TypeBreakdown, format_report, score_submission

    assert score_submission is not None
    assert EvalReport is not None
    assert TypeBreakdown is not None
    assert format_report is not None
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_package_exports.py -v`
Expected: FAIL với `ImportError: cannot import name 'score_submission' from 'eval_harness'`

- [ ] **Step 3: Viết `src/eval_harness/__init__.py`**

```python
"""Chấm điểm submission.jsonl theo rulebook.md §9 — xem specs/003-eval-harness/spec.md."""
from .report import EvalReport, TypeBreakdown, format_report
from .scoring import score_submission

__all__ = [
    "EvalReport",
    "TypeBreakdown",
    "format_report",
    "score_submission",
]
```

- [ ] **Step 4: Viết `src/eval_harness/cli.py`**

```python
"""CLI mỏng chấm điểm submission — xem specs/003-eval-harness/spec.md."""
from __future__ import annotations

import argparse

from .report import format_report
from .scoring import score_submission


def main() -> None:
    parser = argparse.ArgumentParser(description="Chấm điểm submission theo rulebook.md §9")
    parser.add_argument("--questions", required=True)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--submission", required=True)
    args = parser.parse_args()

    report = score_submission(args.questions, args.answers, args.submission)
    print(format_report(report))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Chạy test export, xác nhận PASS**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/test_package_exports.py -v`
Expected: 1 passed

- [ ] **Step 6: Chạy CLI tay 1 lần trên dữ liệu thật để xác nhận hoạt động**

Dùng `tempfile` (stdlib, chạy đúng trên cả Windows/Linux, không hard-code `/tmp`):

```bash
.venv/Scripts/python -c "
import json
import tempfile
import pathlib

rows = []
with open('train/answers.jsonl', encoding='utf-8') as f:
    for line in f:
        a = json.loads(line)
        rows.append({'id': a['id'], 'type': a['type'], 'answer': a['answer']})

out_path = pathlib.Path(tempfile.gettempdir()) / 'eval_harness_manual_check.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + chr(10))
print(out_path)
"
```

Lấy đường dẫn in ra ở trên (gọi là `OUT_PATH`), rồi chạy:

```bash
.venv/Scripts/python -m eval_harness.cli --questions train/questions.jsonl --answers train/answers.jsonl --submission OUT_PATH
```

Expected: in ra report với `Accuracy: 1.0000`. Xoá file tạm (`OUT_PATH`) sau khi kiểm xong — chỉ là bước
kiểm tay, không phải artifact commit.

- [ ] **Step 7: Chạy toàn bộ test của sub-project này, xác nhận PASS hết**

Run: `.venv/Scripts/python -m pytest tests/eval_harness/ -v`
Expected: 38 passed (14 + 12 + 3 + 8 + 1 = 38)

- [ ] **Step 8: Commit**

```bash
git add src/eval_harness/__init__.py src/eval_harness/cli.py tests/eval_harness/test_package_exports.py
git commit -m "feat(eval-harness): export public API and add thin CLI"
```
