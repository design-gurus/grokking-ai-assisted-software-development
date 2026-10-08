import pytest

from review_assistant.providers.base import ProviderError
from review_assistant.providers.retry import RetryPolicy


def test_retries_the_configured_number_of_times() -> None:
    policy = RetryPolicy(retries=3)
    waits: list[float] = []
    policy.sleep = waits.append
    calls = 0

    def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 4:
            raise ProviderError("try again")
        return "ok"

    assert policy.run(flaky) == "ok"
    assert calls == 4
    assert waits == [0.5, 1.0, 2.0]


def test_gives_up_after_the_last_retry() -> None:
    policy = RetryPolicy(retries=1)
    policy.sleep = lambda _: None

    def always() -> str:
        raise ProviderError("down")

    with pytest.raises(ProviderError):
        policy.run(always)


def test_the_delay_is_capped() -> None:
    assert RetryPolicy(retries=9, cap=4.0).delay(9) == 4.0
