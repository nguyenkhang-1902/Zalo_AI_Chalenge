from distill.dataset_builder import build_sft_records


def test_filters_dedupes_and_excludes_devset():
    msg = [{"role": "user", "content": "x"}]
    recs = [
        {"id": "a", "business_id": "b1", "status": "verified", "messages": msg},
        {"id": "a2", "business_id": "b1", "status": "verified", "messages": msg},  # trùng nội dung
        {"id": "dev", "business_id": "b1", "status": "verified", "messages": [{"role": "user", "content": "y"}]},
        {"id": "f", "business_id": "b1", "status": "failed", "messages": None},
    ]
    out = build_sft_records(recs, devset_ids={"dev"})
    assert len(out) == 1  # dedupe trùng + loại dev + bỏ failed
    assert out[0]["messages"] == msg and out[0]["meta"]["id"] == "a"
