from accuracy_boost.config import load_boost_config


def test_defaults(monkeypatch):
    for name in ("N_RUNS", "THRESHOLD", "SAMPLE_TEMPERATURE", "BASE_SEED"):
        monkeypatch.delenv(f"ACCURACY_BOOST_{name}", raising=False)
    cfg = load_boost_config()
    assert (cfg.n_runs, cfg.threshold, cfg.sample_temperature, cfg.base_seed) == (3, 0.6, 0.7, 42)


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("ACCURACY_BOOST_N_RUNS", "5")
    monkeypatch.setenv("ACCURACY_BOOST_THRESHOLD", "0.8")
    cfg = load_boost_config()
    assert cfg.n_runs == 5 and cfg.threshold == 0.8
