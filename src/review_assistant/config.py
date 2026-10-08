"""The per-repository configuration: `.review-assistant.yml` at the root, with environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from review_assistant.findings.filter import ORDER

CONFIG_FILE = ".review-assistant.yml"
PROVIDERS = ("mock", "anthropic", "openai")


class ConfigError(ValueError):
    """A configuration value is not one the service accepts."""


@dataclass
class Config:
    """Every setting the service reads, with the defaults a fresh clone runs on."""

    provider: str = "mock"
    model: str = "mock-review-1"
    severity_floor: str = "low"
    ledger_path: str = "ledger.sqlite"
    model_limit: int = 200_000
    reserved_for_reply: int = 4_000
    request_template_version: int = 1
    replies_dir: str = "fixtures/replies"
    github_token: str = ""
    webhook_secret: str = ""
    extra: dict[str, object] = field(default_factory=dict)


def load_config(path: str | Path = CONFIG_FILE) -> Config:
    """Read the config file if it exists, apply environment overrides, and validate.

    A missing file gives the defaults. `REVIEW_PROVIDER` and `REVIEW_MODEL` override the file.
    A floor outside the four severities is rejected with the allowed list in the message.
    """
    data: dict[str, object] = {}
    file = Path(path)
    if file.exists():
        loaded = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ConfigError(f"{file} must hold a mapping at the top level")
        data = dict(loaded)
    config = Config()
    for name in (
        "provider",
        "model",
        "severity_floor",
        "ledger_path",
        "model_limit",
        "reserved_for_reply",
        "request_template_version",
        "replies_dir",
    ):
        if name in data:
            setattr(config, name, data.pop(name))
    config.extra = data
    config.provider = os.environ.get("REVIEW_PROVIDER", config.provider)
    config.model = os.environ.get("REVIEW_MODEL", config.model)
    config.github_token = os.environ.get("GITHUB_TOKEN", config.github_token)
    config.webhook_secret = os.environ.get("REVIEW_WEBHOOK_SECRET", config.webhook_secret)
    validate(config)
    return config


def validate(config: Config) -> None:
    """Reject values the rest of the service would misread."""
    if config.severity_floor not in ORDER:
        raise ConfigError(f"severity_floor must be one of {', '.join(ORDER)}; got {config.severity_floor!r}")
    if config.provider not in PROVIDERS:
        raise ConfigError(f"provider must be one of {', '.join(PROVIDERS)}; got {config.provider!r}")
    if config.reserved_for_reply >= config.model_limit:
        raise ConfigError("reserved_for_reply must be smaller than model_limit")
    if config.request_template_version < 1:
        raise ConfigError("request_template_version starts at 1")
