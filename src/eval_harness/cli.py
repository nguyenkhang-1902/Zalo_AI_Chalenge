"""CLI mỏng chấm điểm submission — xem specs/003-eval-harness/spec.md."""
from __future__ import annotations

import argparse
import sys

from .report import format_report
from .scoring import score_submission


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Chấm điểm submission theo rulebook.md §9")
    parser.add_argument("--questions", required=True)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--submission", required=True)
    args = parser.parse_args()

    report = score_submission(args.questions, args.answers, args.submission)
    print(format_report(report))


if __name__ == "__main__":
    main()
