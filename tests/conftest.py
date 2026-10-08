from __future__ import annotations

from pathlib import Path

import pytest

from review_assistant.config import Config
from review_assistant.providers.mock import MockProvider
from tests.helpers import REPLIES


@pytest.fixture
def config(tmp_path: Path) -> Config:
    """The default config with the ledger in a temporary file."""
    return Config(ledger_path=str(tmp_path / "ledger.sqlite"), replies_dir=str(REPLIES))


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider(REPLIES)
