import json
from pathlib import Path

from accuracy_boost.measure import collect_runs, format_curve, load_runs, mean_elapsed
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


def test_resume_tolerates_truncated_last_line(tmp_path):
    out = tmp_path / "runs.jsonl"

    def run_fn(question, business_id, as_of_date, dataset_dir, options):
        return {"type": "number", "answer": options.seed}

    kwargs = dict(n_runs=2, sample_temperature=0.7, base_options=AgentOptions(seed=10), run_fn=run_fn)
    collect_runs(DEV[:1], Path("."), out, **kwargs)
    lines = out.read_text(encoding="utf-8").splitlines()
    out.write_text(lines[0] + "\n" + lines[1][:20], encoding="utf-8")

    assert collect_runs(DEV[:1], Path("."), out, **kwargs) == 1
    assert [r["answer"] for r in load_runs(out)["q1"]] == [10, 11]
    assert mean_elapsed(out) >= 0.0


def test_errored_run_is_retried_and_later_row_wins(tmp_path):
    out = tmp_path / "runs.jsonl"
    calls = []

    def run_fn(question, business_id, as_of_date, dataset_dir, options):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("timeout")
        return {"type": "number", "answer": 42}

    kwargs = dict(n_runs=1, sample_temperature=0.7, base_options=AgentOptions(), run_fn=run_fn)
    assert collect_runs(DEV[:1], Path("."), out, **kwargs) == 1
    assert load_runs(out)["q1"][0]["type"] == "abstain"
    assert collect_runs(DEV[:1], Path("."), out, **kwargs) == 1
    assert load_runs(out)["q1"] == [{"type": "number", "answer": 42}]


def test_collect_cli_excludes_dev_questions_from_fewshot(tmp_path, monkeypatch):
    from accuracy_boost import measure

    captured = {}

    def fake_collect(devset, dataset_dir, out_path, **kwargs):
        captured["extra"] = kwargs["base_options"].prompt_extra_fn(devset[0]["question"])
        return 0

    train = tmp_path / "train"
    train.mkdir()
    (train / "rulebook.md").write_text("r", encoding="utf-8")
    (train / "calendar.csv").write_text("c", encoding="utf-8")
    questions = [{"id": f"q{i}", "business_id": "b", "question": f"doanh thu thang {i}", "as_of_date": "2026-01-01"} for i in range(6)]
    (train / "questions.jsonl").write_text("".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8")
    (train / "answers.jsonl").write_text("".join(json.dumps({"id": q["id"], "type": "number", "answer": 1, "alias": []}) + "\n" for q in questions), encoding="utf-8")

    monkeypatch.setattr(measure, "collect_runs", fake_collect)
    monkeypatch.setattr(measure, "prepare_dataset_dir", lambda *a, **k: None)
    measure.main(["collect", "--train-dir", str(train), "--dataset-dir", str(tmp_path / "d"),
                  "--out", str(tmp_path / "o.jsonl"), "--size", "6", "--fewshot-k", "3"])
    assert captured["extra"] == ""


def test_collect_cli_limit_still_excludes_full_devset_from_fewshot(tmp_path, monkeypatch):
    from accuracy_boost import measure
    from accuracy_boost.devset import build_devset

    captured = {}

    def fake_collect(devset, dataset_dir, out_path, **kwargs):
        captured["subset"] = [q["question"] for q in devset]
        captured["extra"] = kwargs["base_options"].prompt_extra_fn(devset[0]["question"])
        return 0

    train = tmp_path / "train"
    train.mkdir()
    (train / "rulebook.md").write_text("r", encoding="utf-8")
    (train / "calendar.csv").write_text("c", encoding="utf-8")
    questions = [{"id": f"q{i}", "business_id": "b", "question": f"doanh thu thang {i}", "as_of_date": "2026-01-01"} for i in range(8)]
    answers = {q["id"]: {"id": q["id"], "type": "number", "answer": 1, "alias": []} for q in questions}
    (train / "questions.jsonl").write_text("".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8")
    (train / "answers.jsonl").write_text("".join(json.dumps(a) + "\n" for a in answers.values()), encoding="utf-8")

    monkeypatch.setattr(measure, "collect_runs", fake_collect)
    monkeypatch.setattr(measure, "prepare_dataset_dir", lambda *a, **k: None)
    measure.main(["collect", "--train-dir", str(train), "--dataset-dir", str(tmp_path / "d"),
                  "--out", str(tmp_path / "o.jsonl"), "--size", "6", "--limit", "2", "--fewshot-k", "8"])

    full_dev = {q["question"] for q in build_devset(questions, answers, size=6)}
    assert len(captured["subset"]) == 2 and len(full_dev) == 6
    assert captured["extra"] != ""
    assert not any(f'"{text}"' in captured["extra"] for text in full_dev)


def test_collect_cli_passes_fewshot_max_chars(tmp_path, monkeypatch):
    from accuracy_boost import measure

    captured = {}

    def fake_collect(devset, dataset_dir, out_path, **kwargs):
        captured["extra"] = kwargs["base_options"].prompt_extra_fn("doanh thu thang x")
        return 0

    train = tmp_path / "train"
    train.mkdir()
    (train / "rulebook.md").write_text("r", encoding="utf-8")
    (train / "calendar.csv").write_text("c", encoding="utf-8")
    questions = [{"id": f"q{i}", "business_id": "b", "question": f"doanh thu thang {i}", "as_of_date": "2026-01-01"} for i in range(8)]
    (train / "questions.jsonl").write_text("".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8")
    (train / "answers.jsonl").write_text("".join(json.dumps({"id": q["id"], "type": "number", "answer": 1, "alias": []}) + "\n" for q in questions), encoding="utf-8")

    monkeypatch.setattr(measure, "collect_runs", fake_collect)
    monkeypatch.setattr(measure, "prepare_dataset_dir", lambda *a, **k: None)
    measure.main(["collect", "--train-dir", str(train), "--dataset-dir", str(tmp_path / "d"),
                  "--out", str(tmp_path / "o.jsonl"), "--size", "2", "--fewshot-k", "8", "--fewshot-max-chars", "40"])
    assert captured["extra"] == ""
