"""Tham số cổng tin cậy — Điều 4: mọi ngưỡng ở config/env, không magic value."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BoostConfig:
    n_runs: int
    threshold: float
    sample_temperature: float
    base_seed: int


def load_boost_config() -> BoostConfig:
    return BoostConfig(
        n_runs=int(os.environ.get("ACCURACY_BOOST_N_RUNS", "3")),
        threshold=float(os.environ.get("ACCURACY_BOOST_THRESHOLD", "0.6")),
        sample_temperature=float(os.environ.get("ACCURACY_BOOST_SAMPLE_TEMPERATURE", "0.7")),
        base_seed=int(os.environ.get("ACCURACY_BOOST_BASE_SEED", "42")),
    )
