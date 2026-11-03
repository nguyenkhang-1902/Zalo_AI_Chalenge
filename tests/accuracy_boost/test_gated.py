from datetime import date
from pathlib import Path

import pytest

from accuracy_boost.gated import answer_with_gate, make_gated_answer_fn, options_for_run
from reasoning_agent.options import AgentOptions

A = {"type": "number", "answer": 1}
B = {"type": "number", "answer": 2}


def _scripted(results):
    calls = []

    def run_fn(question, business_id, as_of_date, dataset_dir, options):
        calls.append(options)
        return results[len(calls) - 1]

    run_fn.calls = calls
    return run_fn


def test_run_zero_is_greedy_and_others_sample_with_distinct_seeds():
    base = AgentOptions(seed=42)
    assert options_for_run(base, 0, 0.7).temperature == 0.0
    assert options_for_run(base, 0, 0.7).seed == 42
    assert options_for_run(base, 2, 0.7).temperature == 0.7
    assert options_for_run(base, 2, 0.7).seed == 44


def test_returns_majority_answer():
    run_fn = _scripted([A, B, A])
    result = answer_with_gate("q", "b", date(2026, 1, 1), Path("."), n_runs=3, threshold=0.6, sample_temperature=0.7, run_fn=run_fn)
    assert result == A
    assert len(run_fn.calls) == 3


def test_abstains_without_agreement():
    run_fn = _scripted([A, B, {"type": "string", "answer": "x"}])
    result = answer_with_gate("q", "b", date(2026, 1, 1), Path("."), n_runs=3, threshold=0.6, sample_temperature=0.7, run_fn=run_fn)
    assert result == {"type": "abstain"}


def test_run_exception_counts_as_abstain_vote_but_missing_files_propagate():
    def flaky(question, business_id, as_of_date, dataset_dir, options):
        if options.seed == 43:
            raise RuntimeError("boom")
        return A

    result = answer_with_gate("q", "b", date(2026, 1, 1), Path("."), n_runs=3, threshold=0.6, sample_temperature=0.7, base_options=AgentOptions(seed=42), run_fn=flaky)
    assert result == A

    def infra(question, business_id, as_of_date, dataset_dir, options):
        raise FileNotFoundError("rulebook.md")

    with pytest.raises(FileNotFoundError):
        answer_with_gate("q", "b", date(2026, 1, 1), Path("."), n_runs=3, threshold=0.6, sample_temperature=0.7, run_fn=infra)


def test_make_gated_answer_fn_matches_runner_signature():
    fn = make_gated_answer_fn(n_runs=2, threshold=0.5, sample_temperature=0.7, run_fn=_scripted([A, A]))
    assert fn("q", "b", date(2026, 1, 1), Path(".")) == A
