"""Retry a provider call a fixed number of times with exponential backoff."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from review_assistant.providers.base import ProviderError

T = TypeVar("T")


class RetryPolicy:
    """How many times to retry a failed call, and how long to wait between attempts.

    `retries` is the number of attempts after the first. Extra keyword options are accepted for
    tuning the backoff: `base_delay` in seconds, and `cap` as the longest single wait.
    """

    def __init__(self, retries: int = 0, **options: float) -> None:
        """Set the retry count and the backoff options."""
        self.retries = retries
        self.base_delay = float(options.get("base_delay", 0.5))
        self.cap = float(options.get("cap", 30.0))
        self.sleep: Callable[[float], None] = time.sleep

    def delay(self, attempt: int) -> float:
        """Compute the wait before attempt number `attempt`, counted from one."""
        wait: float = min(self.base_delay * (2 ** (attempt - 1)), self.cap)
        return wait

    def run(self, call: Callable[[], T]) -> T:
        """Call once, then retry on ProviderError up to `retries` more times."""
        attempt = 0
        while True:
            try:
                return call()
            except ProviderError:
                attempt += 1
                if attempt > self.retries:
                    raise
                self.sleep(self.delay(attempt))
