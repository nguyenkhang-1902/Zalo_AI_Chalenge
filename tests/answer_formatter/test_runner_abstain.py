import json

from answer_formatter.runner import run_batch


def test_abstain_result_is_not_written_and_not_an_error(tmp_path):
    questions = tmp_path / "q.jsonl"
    questions.write_text(
        "".join(
            json.dumps({"id": i, "business_id": "b", "question": "x", "as_of_date": "2026-01-01"}) + "\n"
            for i in ("q1", "q2")
        ),
        encoding="utf-8",
    )

    calls = []

    def answer_fn(question, business_id, as_of_date, dataset_dir):
        calls.append(1)
        return {"type": "abstain"} if len(calls) == 1 else {"type": "number", "answer": 1}

    out = tmp_path / "submission.jsonl"
    summary = run_batch(questions, tmp_path, out, answer_fn=answer_fn)

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in rows] == ["q2"]
    assert summary.abstained == 1
    assert summary.errored == 0
