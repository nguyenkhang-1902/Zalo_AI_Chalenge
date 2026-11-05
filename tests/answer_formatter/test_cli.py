"""Test CLI — FR-010, xem specs/005-answer-formatter/spec.md."""
from __future__ import annotations

from pathlib import Path

import pytest

from answer_formatter import cli
from answer_formatter.runner import BatchSummary


def test_cli_parses_args_and_calls_run_batch(tmp_path, monkeypatch, capsys):
    captured = {}

    def fake_run_batch(questions_path, dataset_dir, out_path, concurrency=1, limit=None, **kwargs):
        captured["questions_path"] = questions_path
        captured["dataset_dir"] = dataset_dir
        captured["out_path"] = out_path
        captured["concurrency"] = concurrency
        captured["limit"] = limit
        return BatchSummary(total=1, resumed_skipped=0, processed=1, errored=0, elapsed_seconds=0.1)

    monkeypatch.setattr(cli, "run_batch", fake_run_batch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "answer-formatter",
            "--questions", str(tmp_path / "q.jsonl"),
            "--dataset-dir", str(tmp_path),
            "--out", str(tmp_path / "out.jsonl"),
            "--concurrency", "4",
            "--limit", "10",
        ],
    )

    cli.main()

    assert captured["questions_path"] == Path(tmp_path / "q.jsonl")
    assert captured["dataset_dir"] == Path(tmp_path)
    assert captured["out_path"] == Path(tmp_path / "out.jsonl")
    assert captured["concurrency"] == 4
    assert captured["limit"] == 10

    out = capsys.readouterr().out
    assert "Tổng: 1" in out


def test_cli_limit_defaults_to_none_when_omitted(tmp_path, monkeypatch):
    captured = {}

    def fake_run_batch(questions_path, dataset_dir, out_path, concurrency=1, limit=None, **kwargs):
        captured["limit"] = limit
        captured["concurrency"] = concurrency
        return BatchSummary(total=0, resumed_skipped=0, processed=0, errored=0, elapsed_seconds=0.0)

    monkeypatch.setattr(cli, "run_batch", fake_run_batch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "answer-formatter",
            "--questions", str(tmp_path / "q.jsonl"),
            "--dataset-dir", str(tmp_path),
            "--out", str(tmp_path / "out.jsonl"),
        ],
    )

    cli.main()

    assert captured["limit"] is None
    assert captured["concurrency"] == 1


def test_all_public_symbols_importable_from_package_root():
    from answer_formatter import BatchSummary, run_batch

    assert run_batch is not None
    assert BatchSummary is not None


def test_cli_exits_nonzero_when_all_processed_questions_error(tmp_path, monkeypatch):
    def fake_run_batch(questions_path, dataset_dir, out_path, concurrency=1, limit=None, **kwargs):
        return BatchSummary(total=2, resumed_skipped=0, processed=2, errored=2, elapsed_seconds=0.1)

    monkeypatch.setattr(cli, "run_batch", fake_run_batch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "answer-formatter",
            "--questions", str(tmp_path / "q.jsonl"),
            "--dataset-dir", str(tmp_path),
            "--out", str(tmp_path / "out.jsonl"),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 1


def test_cli_gate_flag_passes_gated_answer_fn(tmp_path, monkeypatch):
    captured = {}

    def fake_run_batch(questions_path, dataset_dir, out_path, concurrency=1, limit=None, **kwargs):
        captured.update(kwargs)
        return BatchSummary(total=1, resumed_skipped=0, processed=1, errored=0, elapsed_seconds=0.1)

    monkeypatch.setattr(cli, "run_batch", fake_run_batch)
    monkeypatch.setattr(
        "sys.argv",
        ["answer-formatter", "--questions", str(tmp_path / "q.jsonl"),
         "--dataset-dir", str(tmp_path), "--out", str(tmp_path / "o.jsonl"), "--gate"],
    )
    cli.main()
    assert callable(captured["answer_fn"])
