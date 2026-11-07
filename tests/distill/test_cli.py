import json
from datetime import date

from distill.cli import run_generation
from distill.trace_generator import TraceResult


def _collect_ok(q, b, d, dd, tc, tt, ta, al, **k):
    return TraceResult(result={"type": tt, "answer": ta}, messages=[{"role": "user"}])


def test_excludes_devset_and_resumes(tmp_path):
    qs = [
        {"id": "a", "business_id": "b1", "question": "?", "as_of_date": "2026-03-29"},
        {"id": "dev", "business_id": "b1", "question": "?", "as_of_date": "2026-03-29"},
        {"id": "c", "business_id": "b1", "question": "?", "as_of_date": "2026-03-29"},
    ]
    ans = {q["id"]: {"type": "number", "answer": 1, "alias": []} for q in qs}
    out = tmp_path / "traces.jsonl"

    c1 = run_generation(qs, ans, tmp_path, out, devset_ids={"dev"}, collect_fn=_collect_ok)
    ids = [json.loads(line)["id"] for line in out.read_text(encoding="utf-8").splitlines()]
    assert ids == ["a", "c"] and c1["verified"] == 2  # "dev" bị loại

    # resume: chạy lại không thêm dòng
    run_generation(qs, ans, tmp_path, out, devset_ids={"dev"}, collect_fn=_collect_ok)
    ids2 = [json.loads(line)["id"] for line in out.read_text(encoding="utf-8").splitlines()]
    assert ids2 == ["a", "c"]


def test_one_bad_question_does_not_crash_batch(tmp_path):
    qs = [
        {"id": "a", "business_id": "b1", "question": "?", "as_of_date": "2026-03-29"},
        {"id": "boom", "business_id": "b1", "question": "?", "as_of_date": "2026-03-29"},
        {"id": "c", "business_id": "b1", "question": "?", "as_of_date": "2026-03-29"},
    ]
    ans = {q["id"]: {"type": "number", "answer": 1, "alias": []} for q in qs}
    calls = {"n": 0}

    def collect_raising(question, business_id, as_of_date, dataset_dir, tc, tt, ta, al, **k):
        calls["n"] += 1
        if calls["n"] == 2:  # câu thứ 2 ("boom") ném lỗi — không được làm sập cả batch
            raise RuntimeError("gateway 500")
        return TraceResult(result={"type": tt, "answer": ta}, messages=[{"role": "user"}])

    out = tmp_path / "t.jsonl"
    counts = run_generation(qs, ans, tmp_path, out, devset_ids=set(), collect_fn=collect_raising)
    by_id = {json.loads(line)["id"]: json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()}
    assert counts == {"verified": 2, "failed": 1, "skipped": 0}
    assert by_id["boom"]["status"] == "failed" and "gateway 500" in by_id["boom"]["error"]
    assert by_id["a"]["status"] == "verified" and by_id["c"]["status"] == "verified"
