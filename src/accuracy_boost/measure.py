"""Thu kết quả N lần cho bộ dev (có resume) rồi tính PA theo ngưỡng — FR-002/FR-007.

Dùng:
  python -m accuracy_boost.measure collect --dataset-dir build_output/dev --out logs/base.jsonl [--limit 60]
  python -m accuracy_boost.measure report --runs logs/base.jsonl
Chỉ đọc train/ (FR-009)."""
from __future__ import annotations

import argparse
import json
import shutil
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Callable

from accuracy_boost.config import load_boost_config
from accuracy_boost.consensus import pa_curve
from accuracy_boost.devset import build_devset, take_subset
from accuracy_boost.fewshot import FewShotPool
from accuracy_boost.gated import options_for_run
from data_loader.build_business_db import build_business
from reasoning_agent import answer_question
from reasoning_agent.options import AgentOptions
from reasoning_agent.react_loop import BUDGET_EXHAUSTED_REASON

DEFAULT_TRAIN_DIR = Path("train")
FAST_FAILURE_SECONDS = 2.0  # hết ngân sách thật mất nhiều giây; server chết thì trả về gần như tức thì


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _load_runs_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # dòng cụt do collector bị kill giữa chừng
    return rows


def prepare_dataset_dir(train_dir: Path, business_ids: list[str], dataset_dir: Path) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    for name in ("rulebook.md", "calendar.csv"):
        shutil.copy(train_dir / name, dataset_dir / name)
    for business_id in business_ids:
        if not (dataset_dir / f"{business_id}.duckdb").exists():
            build_business(train_dir / "data" / business_id, dataset_dir)


def _is_budget_exhausted(row: dict) -> bool:
    result = row["result"]
    return result.get("type") == "unanswerable" and result.get("reason") == BUDGET_EXHAUSTED_REASON


def _is_fast_budget_exhausted(row: dict) -> bool:
    return _is_budget_exhausted(row) and row.get("elapsed", 0.0) < FAST_FAILURE_SECONDS


def _done_keys(path: Path) -> set[tuple[str, int]]:
    if not path.exists():
        return set()
    done = set()
    for row in _load_runs_rows(path):
        if "error" not in row["result"] and not _is_fast_budget_exhausted(row):
            done.add((row["id"], row["run"]))
    return done


def collect_runs(
    devset: list[dict],
    dataset_dir: Path,
    out_path: Path,
    *,
    n_runs: int,
    sample_temperature: float,
    base_options: AgentOptions,
    run_fn: Callable[..., dict] = answer_question,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = _done_keys(out_path)
    written = 0
    if out_path.exists() and out_path.stat().st_size:
        with out_path.open("rb") as f:
            f.seek(-1, 2)
            needs_newline = f.read(1) != b"\n"
        if needs_newline:
            with out_path.open("a", encoding="utf-8") as f:
                f.write("\n")
    with out_path.open("a", encoding="utf-8") as out_file:
        for q in devset:
            for run_index in range(n_runs):
                if (q["id"], run_index) in done:
                    continue
                options = options_for_run(base_options, run_index, sample_temperature)
                started = time.monotonic()
                try:
                    result = run_fn(
                        q["question"], q["business_id"], date.fromisoformat(q["as_of_date"]), dataset_dir, options=options
                    )
                except FileNotFoundError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    result = {"type": "abstain", "error": str(exc)}
                row = {"id": q["id"], "run": run_index, "elapsed": round(time.monotonic() - started, 2), "result": result}
                out_file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                out_file.flush()
                written += 1
    return written


def load_runs(path: Path) -> dict[str, list[dict]]:
    by_id: dict[str, dict[int, dict]] = defaultdict(dict)
    for row in _load_runs_rows(path):
        by_id[row["id"]][row["run"]] = row["result"]
    return {qid: [runs[i] for i in sorted(runs)] for qid, runs in by_id.items()}


def mean_elapsed(path: Path) -> float:
    rows = _load_runs_rows(path)
    return sum(r["elapsed"] for r in rows) / len(rows) if rows else 0.0


def format_curve(rows: list[dict]) -> str:
    lines = ["| threshold | PA | correct | wrong | abstained |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['threshold']} | {r['pa']:.3f} | {r['correct']} | {r['wrong']} | {r['abstained']} |")
    return "\n".join(lines)


def _build_options(args, train_dir: Path, exclude_questions: frozenset[str]) -> AgentOptions:
    prompt_extra_fn = None
    if args.fewshot_k > 0:
        pool = FewShotPool.from_train_dir(train_dir)

        def prompt_extra_fn(question: str) -> str:
            return pool.format_prompt(question, args.fewshot_k, exclude_questions, args.fewshot_max_chars)

    return AgentOptions(
        seed=load_boost_config().base_seed, semantic_tools=args.semantic_tools, prompt_extra_fn=prompt_extra_fn
    )


def _cmd_collect(args) -> int:
    train_dir = Path(args.train_dir)
    questions = _load_jsonl(train_dir / "questions.jsonl")
    answers_by_id = {a["id"]: a for a in _load_jsonl(train_dir / "answers.jsonl")}
    full_dev = build_devset(questions, answers_by_id, size=args.size)
    devset = take_subset(full_dev, args.limit) if args.limit else full_dev
    prepare_dataset_dir(train_dir, sorted({q["business_id"] for q in devset}), Path(args.dataset_dir))
    cfg = load_boost_config()
    exclude = frozenset(q["question"] for q in full_dev)
    written = collect_runs(
        devset,
        Path(args.dataset_dir),
        Path(args.out),
        n_runs=args.n_runs or cfg.n_runs,
        sample_temperature=cfg.sample_temperature,
        base_options=_build_options(args, train_dir, exclude),
    )
    print(f"đã ghi {written} lượt chạy vào {args.out}")
    return 0


def _cmd_report(args) -> int:
    train_dir = Path(args.train_dir)
    answers_by_id = {a["id"]: a for a in _load_jsonl(train_dir / "answers.jsonl")}
    runs = load_runs(Path(args.runs))
    thresholds = [float(t) for t in args.thresholds.split(",")]
    print("### Greedy (chỉ run 0, trả lời mọi câu)")
    greedy = {qid: results[:1] for qid, results in runs.items()}
    print(format_curve(pa_curve(greedy, answers_by_id, [0.0])))
    print("\n### Cổng tin cậy theo ngưỡng")
    print(format_curve(pa_curve(runs, answers_by_id, thresholds)))
    exhausted = [r for r in _load_runs_rows(Path(args.runs)) if _is_budget_exhausted(r)]
    fast = sum(_is_fast_budget_exhausted(r) for r in exhausted)
    print(f"\nbudget-exhausted: {len(exhausted)} (fast: {fast}) — fast cao nghĩa là server model có thể đã chết")
    print(f"thời gian TB/lượt chạy: {mean_elapsed(Path(args.runs)):.1f}s, số câu: {len(runs)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="accuracy_boost.measure")
    sub = parser.add_subparsers(dest="cmd", required=True)

    collect = sub.add_parser("collect")
    collect.add_argument("--train-dir", default=str(DEFAULT_TRAIN_DIR))
    collect.add_argument("--dataset-dir", required=True)
    collect.add_argument("--out", required=True)
    collect.add_argument("--size", type=int, default=200)
    collect.add_argument("--limit", type=int, default=0)
    collect.add_argument("--n-runs", type=int, default=0)
    collect.add_argument("--semantic-tools", action="store_true")
    collect.add_argument("--fewshot-k", type=int, default=0)
    collect.add_argument("--fewshot-max-chars", type=int, default=1500)
    collect.set_defaults(func=_cmd_collect)

    report = sub.add_parser("report")
    report.add_argument("--train-dir", default=str(DEFAULT_TRAIN_DIR))
    report.add_argument("--runs", required=True)
    report.add_argument("--thresholds", default="0.3,0.6,1.0")
    report.set_defaults(func=_cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
