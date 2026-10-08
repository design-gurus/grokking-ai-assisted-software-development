"""Remember the findings of a reviewed pull request so a redelivery does not pay for the model again."""

from __future__ import annotations

from review_assistant.log import fields, get_logger
from review_assistant.models import Finding

log = get_logger("cache")


class FindingsCache:
    """Findings keyed by pull request number."""

    def __init__(self) -> None:
        """Start empty."""
        self._by_number: dict[int, list[Finding]] = {}

    def findings_for(self, pull_request: int) -> list[Finding] | None:
        """Return the findings last stored for this pull request, or None when it was never reviewed."""
        found = self._by_number.get(pull_request)
        if found is not None:
            log.info("hit         %s", fields(pr=pull_request))
        return list(found) if found is not None else None

    def store(self, pull_request: int, findings: list[Finding]) -> None:
        """Keep these findings as the pull request's current ones."""
        self._by_number[pull_request] = list(findings)

    def forget(self, pull_request: int) -> None:
        """Drop what is stored for a pull request."""
        self._by_number.pop(pull_request, None)
