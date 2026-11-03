"""Test concurrency thật — FR-004/SC-003, xem specs/005-answer-formatter/spec.md."""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from answer_formatter.runner import run_batch

_SLEEP_SECONDS = 0.05
_N_QUESTIONS = 20


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _slow_fn(question: str, business_id: str, as_of_date: date, dataset_dir: Path) -> dict:
    time.sleep(_SLEEP_SECONDS)
    return {"type": "string", "answer": business_id}


def _build_questions(path: Path) -> None:
    _write_jsonl(path, [
        {"id": f"q{i}", "business_id": f"biz_{i}", "question": "a", "as_of_date": "2026-01-01"}
        for i in range(_N_QUESTIONS)
    ])


def test_concurrency_is_meaningfully_faster_than_sequential(tmp_path: Path):
    seq_dir = tmp_path / "seq"
    seq_dir.mkdir()
    questions_path = seq_dir / "questions.jsonl"
    _build_questions(questions_path)
    start = time.monotonic()
    run_batch(questions_path, seq_dir, seq_dir / "out.jsonl", concurrency=1, answer_fn=_slow_fn)
    sequential_elapsed = time.monotonic() - start

    par_dir = tmp_path / "par"
    par_dir.mkdir()
    questions_path2 = par_dir / "questions.jsonl"
    _build_questions(questions_path2)
    start = time.monotonic()
    run_batch(questions_path2, par_dir, par_dir / "out.jsonl", concurrency=4, answer_fn=_slow_fn)
    concurrent_elapsed = time.monotonic() - start

    assert concurrent_elapsed < sequential_elapsed * 0.6, (
        f"concurrency=4 ({concurrent_elapsed:.2f}s) không nhanh hơn rõ rệt so với "
        f"concurrency=1 ({sequential_elapsed:.2f}s)"
    )


def test_concurrency_writes_all_lines_without_duplication_or_loss(tmp_path: Path):
    questions_path = tmp_path / "questions.jsonl"
    _build_questions(questions_path)
    out_path = tmp_path / "out.jsonl"

    run_batch(questions_path, tmp_path, out_path, concurrency=8, answer_fn=_slow_fn)

    with out_path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    ids = [r["id"] for r in rows]
    assert len(ids) == _N_QUESTIONS
    assert len(set(ids)) == _N_QUESTIONS
