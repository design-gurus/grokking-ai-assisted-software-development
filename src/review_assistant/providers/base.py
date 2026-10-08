"""The provider interface and the factory that picks a backend by name."""

from __future__ import annotations

from typing import Protocol

from review_assistant.config import Config
from review_assistant.models import Reply, Request


class ProviderError(RuntimeError):
    """A provider call failed in a way that may succeed on retry."""


class Provider(Protocol):
    """What every backend offers: a name and one call that turns a request into a reply."""

    name: str

    def complete(self, request: Request) -> Reply:
        """Send the request and return the reply."""
        ...


def get_provider(config: Config) -> Provider:
    """Build the backend named in the config, with the config's settings."""
    if config.provider == "mock":
        from review_assistant.providers.mock import MockProvider

        return MockProvider(config.replies_dir)
    if config.provider == "anthropic":
        from review_assistant.providers.anthropic import AnthropicProvider
        from review_assistant.providers.retry import RetryPolicy

        return AnthropicProvider(model=config.model, policy=RetryPolicy(retries=3))
    if config.provider == "openai":
        from review_assistant.providers.openai import OpenAIProvider
        from review_assistant.providers.retry import RetryPolicy

        return OpenAIProvider(model=config.model, policy=RetryPolicy(retries=3))
    raise ValueError(f"unknown provider {config.provider!r}")
