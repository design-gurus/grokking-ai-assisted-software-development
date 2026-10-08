from pathlib import Path

import pytest

from review_assistant.config import Config
from review_assistant.providers.registry import ProviderRegistry
from tests.helpers import REPLIES


def test_the_registry_resolves_the_mock(tmp_path: Path) -> None:
    registry = ProviderRegistry.defaults()
    provider = registry.create("mock", Config(replies_dir=str(REPLIES)))
    assert provider.name == "mock"


def test_an_unknown_name_is_refused_with_the_registered_names() -> None:
    with pytest.raises(ValueError) as error:
        ProviderRegistry.defaults().create("nope", Config())
    assert "mock" in str(error.value)
