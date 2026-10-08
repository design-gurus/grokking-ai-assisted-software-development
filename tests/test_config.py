from pathlib import Path

import pytest

from review_assistant.config import Config, ConfigError, load_config


def test_a_missing_file_gives_the_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REVIEW_PROVIDER", raising=False)
    config = load_config(tmp_path / ".review-assistant.yml")
    assert config == Config(github_token=config.github_token, webhook_secret=config.webhook_secret)
    assert config.provider == "mock"
    assert config.severity_floor == "low"


def test_the_file_sets_the_floor_and_the_environment_sets_the_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = tmp_path / ".review-assistant.yml"
    file.write_text("severity_floor: high\nprovider: openai\n", encoding="utf-8")
    monkeypatch.setenv("REVIEW_PROVIDER", "mock")
    config = load_config(file)
    assert config.severity_floor == "high"
    assert config.provider == "mock"


def test_a_bad_floor_is_rejected_with_the_allowed_list(tmp_path: Path) -> None:
    file = tmp_path / ".review-assistant.yml"
    file.write_text("severity_floor: urgent\n", encoding="utf-8")
    with pytest.raises(ConfigError) as error:
        load_config(file)
    assert "low, medium, high, critical" in str(error.value)


def test_unknown_keys_are_kept_aside(tmp_path: Path) -> None:
    file = tmp_path / ".review-assistant.yml"
    file.write_text("future_setting: 1\n", encoding="utf-8")
    assert load_config(file).extra == {"future_setting": 1}
