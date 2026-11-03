"""CLI mỏng chạy batch — FR-010, xem specs/005-answer-formatter/spec.md."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from answer_formatter.runner import run_batch


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Chạy answer_question theo lô, ghi submission.jsonl"
    )
    parser.add_argument("--questions", required=True)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    summary = run_batch(
        questions_path=Path(args.questions),
        dataset_dir=Path(args.dataset_dir),
        out_path=Path(args.out),
        concurrency=args.concurrency,
        limit=args.limit,
    )
    print(
        f"Tổng: {summary.total} | resume-skip: {summary.resumed_skipped} | "
        f"xử lý: {summary.processed} | lỗi: {summary.errored} | "
        f"thời gian: {summary.elapsed_seconds:.1f}s"
    )


if __name__ == "__main__":
    main()
