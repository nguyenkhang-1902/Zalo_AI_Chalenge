from accuracy_boost.devset import build_devset, take_subset


def _data(counts):
    questions, answers = [], {}
    for type_name, n in counts.items():
        for i in range(n):
            qid = f"{type_name}_{i:03d}"
            questions.append({"id": qid, "business_id": "b", "question": qid, "as_of_date": "2026-01-01"})
            answers[qid] = {"type": type_name}
    return questions, answers


def test_stratified_exact_size_and_min_per_type():
    questions, answers = _data({"number": 600, "percent": 300, "table": 5, "boolean": 4})
    dev = build_devset(questions, answers, size=100, seed=1, min_per_type=2)
    assert len(dev) == 100
    types = [answers[q["id"]]["type"] for q in dev]
    assert types.count("table") >= 2 and types.count("boolean") >= 2
    assert types.count("number") > types.count("percent")


def test_deterministic_for_same_seed_and_different_for_other_seed():
    questions, answers = _data({"number": 300, "percent": 100})
    a = build_devset(questions, answers, size=50, seed=7)
    b = build_devset(questions, answers, size=50, seed=7)
    c = build_devset(questions, answers, size=50, seed=8)
    assert [q["id"] for q in a] == [q["id"] for q in b]
    assert [q["id"] for q in a] != [q["id"] for q in c]


def test_take_subset_is_deterministic_prefix_of_shuffle():
    questions, answers = _data({"number": 100})
    dev = build_devset(questions, answers, size=40)
    s1 = take_subset(dev, 10, seed=3)
    assert len(s1) == 10 and [q["id"] for q in s1] == [q["id"] for q in take_subset(dev, 10, seed=3)]
