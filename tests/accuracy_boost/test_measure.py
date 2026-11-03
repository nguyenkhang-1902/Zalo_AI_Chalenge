import json
from datetime import date
from pathlib import Path

from accuracy_boost.measure import collect_runs, format_curve, load_runs
from reasoning_agent.options import AgentOptions

DEV = [
    {"id": "q1", "business_id": "b", "question": "x", "as_of_date": "2026-01-01"},
    {"id": "q2", "business_id": "b", "question": "y", "as_of_date": "2026-01-02"},
]


def test_collect_runs_resumes_and_orders_by_run(tmp_path):
    out = tmp_path / "runs.jsonl"
    seen = []

    def run_fn(question, business_id, as_of_date, dataset_dir, options):
        seen.append((question, options.seed))
        return {"type": "number", "answer": options.seed}

    kwargs = dict(n_runs=3, sample_temperature=0.7, base_options=AgentOptions(seed=10), run_fn=run_fn)
    assert collect_runs(DEV, Path("."), out, **kwargs) == 6

    out.write_text("".join(out.read_text(encoding="utf-8").splitlines(True)[:4]), encoding="utf-8")
    seen.clear()
    assert collect_runs(DEV, Path("."), out, **kwargs) == 2
    assert len(seen) == 2

    runs = load_runs(out)
    assert [r["answer"] for r in runs["q1"]] == [10, 11, 12]
    assert set(runs) == {"q1", "q2"}


def test_exception_in_run_is_recorded_as_abstain_not_crash(tmp_path):
    out = tmp_path / "runs.jsonl"

    def run_fn(*args, **kwargs):
        raise RuntimeError("boom")

    collect_runs(DEV[:1], Path("."), out, n_runs=1, sample_temperature=0.7, base_options=AgentOptions(), run_fn=run_fn)
    row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert row["result"]["type"] == "abstain" and "boom" in row["result"]["error"]


def test_format_curve_is_markdown_table():
    text = format_curve([{"threshold": 0.6, "pa": 0.125, "correct": 3, "wrong": 1, "abstained": 4}])
    assert text.splitlines()[0].startswith("| threshold")
    assert "0.125" in text
