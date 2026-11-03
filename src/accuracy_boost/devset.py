"""Bộ dev cố định từ train/ (SC-001): lấy mẫu phân tầng theo type, tỉ lệ theo phân bố thật để PA
ước lượng đúng điểm trên phân bố của BTC, tối thiểu min_per_type để type hiếm vẫn có mặt."""
from __future__ import annotations

import random
from collections import defaultdict


def build_devset(
    questions: list[dict], answers_by_id: dict, size: int = 200, seed: int = 42, min_per_type: int = 2
) -> list[dict]:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for q in sorted(questions, key=lambda q: q["id"]):
        by_type[answers_by_id[q["id"]]["type"]].append(q)

    total = sum(len(v) for v in by_type.values())
    quotas = {
        t: min(len(v), max(min_per_type, round(size * len(v) / total))) for t, v in by_type.items()
    }
    largest = max(quotas, key=quotas.get)
    quotas[largest] = min(len(by_type[largest]), quotas[largest] - (sum(quotas.values()) - size))

    rng = random.Random(seed)
    sample: list[dict] = []
    for type_name in sorted(by_type):
        items = list(by_type[type_name])
        rng.shuffle(items)
        sample.extend(items[: quotas[type_name]])
    return sorted(sample, key=lambda q: q["id"])


def take_subset(devset: list[dict], n: int, seed: int = 42) -> list[dict]:
    items = list(devset)
    random.Random(seed).shuffle(items)
    return sorted(items[:n], key=lambda q: q["id"])
