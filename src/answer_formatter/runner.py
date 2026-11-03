"""Batch runner (tuần tự) — FR-001/002/003/005/006/007/009/011/012, xem
specs/005-answer-formatter/spec.md. Task 3 sẽ thay nội dung run_batch để thêm concurrency thật,
giữ nguyên chữ ký."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from answer_formatter.normalize import normalize_answer
from reasoning_agent import answer_question

AnswerFn = Callable[[str, str, date, Path], dict]


@dataclass
class BatchSummary:
    total: int
    resumed_skipped: int
    processed: int
    errored: int
    elapsed_seconds: float


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_done_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    done: set[str] = set()
    with out_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                done.add(row["id"])
    return done


def _validate_contract(result: object) -> None:
    if not isinstance(result, dict):
        raise ValueError(f"answer_fn phải trả dict, nhận {type(result).__name__}")
    if "type" not in result:
        raise ValueError("answer_fn thiếu key 'type'")
    if result["type"] != "unanswerable" and "answer" not in result:
        raise ValueError("answer_fn thiếu key 'answer' (type khác unanswerable)")


def _answer_one(question: dict, dataset_dir: Path, answer_fn: AnswerFn) -> tuple[dict, bool]:
    try:
        as_of = date.fromisoformat(question["as_of_date"])
        result = answer_fn(question["question"], question["business_id"], as_of, dataset_dir)
        _validate_contract(result)
    except Exception as exc:  # noqa: BLE001 - 1 câu lỗi không được sập cả batch (FR-007)
        return {"type": "unanswerable", "reason": f"lỗi xử lý: {exc}"}, True
    return normalize_answer(result), False


def run_batch(
    questions_path: Path,
    dataset_dir: Path,
    out_path: Path,
    concurrency: int = 1,
    limit: int | None = None,
    answer_fn: AnswerFn = answer_question,
) -> BatchSummary:
    if concurrency < 1:
        raise ValueError(f"concurrency phải >= 1, nhận {concurrency}")

    start = time.monotonic()
    questions = _load_jsonl(questions_path)

    seen_ids: set[str] = set()
    for q in questions:
        if q["id"] in seen_ids:
            raise ValueError(f"id trùng lặp trong questions_path: {q['id']}")
        seen_ids.add(q["id"])

    done_ids = _load_done_ids(out_path)
    remaining = [q for q in questions if q["id"] not in done_ids]
    if limit is not None:
        remaining = remaining[:limit]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    errored = 0
    with out_path.open("a", encoding="utf-8") as out_file:
        for q in remaining:
            result, is_error = _answer_one(q, dataset_dir, answer_fn)
            if is_error:
                errored += 1
            out_file.write(json.dumps({"id": q["id"], **result}, ensure_ascii=False) + "\n")
            out_file.flush()

    return BatchSummary(
        total=len(questions),
        resumed_skipped=len(done_ids & seen_ids),
        processed=len(remaining),
        errored=errored,
        elapsed_seconds=time.monotonic() - start,
    )
