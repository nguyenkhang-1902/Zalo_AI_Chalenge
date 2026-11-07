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
