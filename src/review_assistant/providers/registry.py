"""A registry of provider backends, with plugin discovery through entry points."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from importlib.metadata import entry_points

from review_assistant.config import Config
from review_assistant.models import Reply, Request
from review_assistant.providers.base import Provider

PLUGIN_GROUP = "review_assistant.providers"


class BaseProvider(ABC):
    """The base class every registered backend extends."""

    name: str = "base"

    @abstractmethod
    def complete(self, request: Request) -> Reply:
        """Send the request and return the reply."""

    def describe(self) -> str:
        """Describe the backend for diagnostics."""
        return f"{self.__class__.__name__}(name={self.name!r})"


class MockBackend(BaseProvider):
    """The mock, registered through the base class."""

    name = "mock"

    def __init__(self, config: Config) -> None:
        """Wrap the mock provider."""
        from review_assistant.providers.mock import MockProvider

        self._inner = MockProvider(config.replies_dir)

    def complete(self, request: Request) -> Reply:
        """Delegate to the mock."""
        return self._inner.complete(request)


class ProviderRegistry:
    """Backends by name, with factories that take the config."""

    def __init__(self) -> None:
        """Start empty; `defaults()` registers the built-in backends."""
        self._factories: dict[str, Callable[[Config], Provider]] = {}
        self._plugins_loaded = False

    def register(self, name: str, factory: Callable[[Config], Provider]) -> None:
        """Register a factory under a name, replacing any earlier one."""
        self._factories[name] = factory

    def names(self) -> list[str]:
        """List every registered name, sorted."""
        return sorted(self._factories)

    def load_plugins(self, group: str = PLUGIN_GROUP) -> int:
        """Register every backend advertised through the entry point group. Returns how many."""
        if self._plugins_loaded:
            return 0
        count = 0
        for entry in entry_points(group=group):
            self.register(entry.name, entry.load())
            count += 1
        self._plugins_loaded = True
        return count

    def create(self, name: str, config: Config) -> Provider:
        """Build the named backend, loading plugins first."""
        self.load_plugins()
        try:
            factory = self._factories[name]
        except KeyError as error:
            raise ValueError(f"unknown provider {name!r}; registered: {', '.join(self.names())}") from error
        return factory(config)

    @classmethod
    def defaults(cls) -> ProviderRegistry:
        """Build a registry with the built-in backends registered."""
        registry = cls()
        registry.register("mock", MockBackend)
        return registry


REGISTRY = ProviderRegistry.defaults()
