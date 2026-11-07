"""CLI sinh dataset trace từ train/: loại câu DevSet (chống rò rỉ), cache/resume theo question_id,
ghi append JSONL mỗi câu. run_generation tách khỏi main để test được (inject collect_fn/devset_ids)."""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date
from pathlib import Path
from typing import Callable

from accuracy_boost.devset import build_devset

from distill.collect import collect_verified_trace
from distill.teacher_config import load_teacher_config


def _done_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    return {
        json.loads(line)["id"]
        for line in out_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def run_generation(
    questions,
    answers_by_id,
    dataset_dir,
    out_path,
    devset_ids,
    collect_fn: Callable = collect_verified_trace,
    max_attempts: int = 3,
    teacher_config=None,
    sleep_seconds: float = 0.0,
) -> dict:
    out_path = Path(out_path)
    done = _done_ids(out_path)
    counts = {"verified": 0, "failed": 0, "skipped": 0}
    with out_path.open("a", encoding="utf-8") as f:
        for q in questions:
            qid = q["id"]
            if qid in devset_ids or qid in done:
                counts["skipped"] += 1
                continue
            g = answers_by_id[qid]
            error = None
            try:
                trace = collect_fn(
                    q["question"],
                    q["business_id"],
                    date.fromisoformat(q["as_of_date"]),
                    dataset_dir,
                    teacher_config,
                    g["type"],
                    g.get("answer"),
                    g.get("alias", []),
                    max_attempts=max_attempts,
                )
            except Exception as e:  # 1 câu lỗi không được làm sập cả batch dài ~3000 câu
                trace = None
                error = str(e)
            rec = {
                "id": qid,
                "business_id": q["business_id"],
                "status": "verified" if trace else "failed",
                "messages": trace.messages if trace else None,
                "tools": trace.tools if trace else None,
            }
            if error:
                rec["error"] = error
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            counts["verified" if trace else "failed"] += 1
            if sleep_seconds:
                time.sleep(sleep_seconds)  # pacing cho gateway free có RPM limit
    return counts


def _read_jsonl(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--questions", required=True)
    p.add_argument("--answers", required=True)
    p.add_argument("--dataset-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--max-attempts", type=int, default=int(os.environ.get("DISTILL_MAX_ATTEMPTS", "3")))
    p.add_argument("--devset-size", type=int, default=200)
    p.add_argument(
        "--sleep-seconds",
        type=float,
        default=float(os.environ.get("DISTILL_SLEEP_SECONDS", "0")),
        help="nghỉ giữa các câu để không vượt RPM của gateway free (0 = không nghỉ)",
    )
    a = p.parse_args()

    questions = _read_jsonl(a.questions)
    answers = {row["id"]: row for row in _read_jsonl(a.answers)}
    devset_ids = {q["id"] for q in build_devset(questions, answers, size=a.devset_size)}
    if a.limit:
        questions = questions[: a.limit]
    counts = run_generation(
        questions,
        answers,
        Path(a.dataset_dir),
        Path(a.out),
        devset_ids,
        max_attempts=a.max_attempts,
        teacher_config=load_teacher_config(),
        sleep_seconds=a.sleep_seconds,
    )
    print("counts:", counts)


if __name__ == "__main__":
    main()
