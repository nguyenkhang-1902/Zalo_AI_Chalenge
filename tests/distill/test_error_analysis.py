from distill.error_analysis import classify_outcomes


def test_classifies_core_buckets():
    gold = {
        "1": {"type": "number", "answer": 10, "alias": []},
        "2": {"type": "number", "answer": 10, "alias": []},
        "3": {"type": "unanswerable", "answer": None, "alias": []},
    }
    preds = [
        {"id": "1", "result": {"type": "number", "answer": 10}},  # correct
        {"id": "2", "result": {"type": "number", "answer": 99}},  # wrong_VALUE
        {"id": "3", "result": {"type": "number", "answer": 1}},  # wrong_should_abstain
    ]
    out = classify_outcomes(preds, gold)
    assert out["correct"] == 1 and out["wrong_VALUE"] == 1 and out["wrong_should_abstain"] == 1
