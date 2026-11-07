import pytest

from distill.teacher_config import load_teacher_config


def test_loads_from_env(monkeypatch):
    monkeypatch.setenv("TEACHER_MODEL", "llama-3.3-70b")
    monkeypatch.setenv("TEACHER_BASE_URL", "https://gw.free/v1/")
    monkeypatch.setenv("TEACHER_API_KEY", "k")
    cfg = load_teacher_config()
    assert (cfg.model, cfg.base_url, cfg.api_key) == ("llama-3.3-70b", "https://gw.free/v1", "k")


def test_missing_model_raises(monkeypatch):
    monkeypatch.delenv("TEACHER_MODEL", raising=False)
    monkeypatch.setenv("TEACHER_BASE_URL", "https://gw.free/v1")
    with pytest.raises(ValueError, match="TEACHER_MODEL"):
        load_teacher_config()
