"""Dựng dataset SFT từ file trace: giữ status=verified, loại DevSet (double-guard), dedupe theo
nội dung messages. Mỗi dòng SFT = {"messages":[...], "meta":{"id","business_id"}}."""
from __future__ import annotations

import json
from pathlib import Path


def build_sft_records(trace_records, devset_ids) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in trace_records:
        if r.get("status") != "verified" or r["id"] in devset_ids or not r.get("messages"):
            continue
        key = json.dumps(r["messages"], ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "messages": r["messages"],
                "tools": r.get("tools"),
                "meta": {"id": r["id"], "business_id": r["business_id"]},
            }
        )
    return out


def write_sft(records, out_path) -> None:
    Path(out_path).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8"
    )


def _read_jsonl(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    import argparse

    from accuracy_boost.devset import build_devset

    p = argparse.ArgumentParser()
    p.add_argument("--traces", required=True)
    p.add_argument("--questions", required=True)
    p.add_argument("--answers", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--devset-size", type=int, default=200)
    a = p.parse_args()

    recs = _read_jsonl(a.traces)
    questions = _read_jsonl(a.questions)
    answers = {row["id"]: row for row in _read_jsonl(a.answers)}
    devset_ids = {q["id"] for q in build_devset(questions, answers, size=a.devset_size)}
    sft = build_sft_records(recs, devset_ids)
    write_sft(sft, a.out)
    print(f"SFT records: {len(sft)}")


if __name__ == "__main__":
    main()
