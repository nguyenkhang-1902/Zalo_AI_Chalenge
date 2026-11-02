import pytest

from reasoning_agent.config import load_config


def test_raises_when_model_env_var_missing(monkeypatch):
    monkeypatch.delenv("REASONING_AGENT_MODEL", raising=False)
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://localhost:11434/v1")

    with pytest.raises(ValueError, match="REASONING_AGENT_MODEL"):
        load_config()


def test_raises_when_base_url_env_var_missing(monkeypatch):
    monkeypatch.setenv("REASONING_AGENT_MODEL", "qwen2.5:7b-instruct")
    monkeypatch.delenv("REASONING_AGENT_BASE_URL", raising=False)

    with pytest.raises(ValueError, match="REASONING_AGENT_BASE_URL"):
        load_config()


def test_loads_config_from_env_vars_and_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("REASONING_AGENT_MODEL", "qwen2.5:7b-instruct")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://localhost:11434/v1/")
    monkeypatch.setenv("REASONING_AGENT_API_KEY", "dummy-key")

    config = load_config()

    assert config.model == "qwen2.5:7b-instruct"
    assert config.base_url == "http://localhost:11434/v1"
    assert config.api_key == "dummy-key"


def test_api_key_defaults_to_empty_string(monkeypatch):
    monkeypatch.setenv("REASONING_AGENT_MODEL", "qwen2.5:7b-instruct")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.delenv("REASONING_AGENT_API_KEY", raising=False)

    config = load_config()

    assert config.api_key == ""
