"""Replay recorded replies, keyed by the SHA-256 of the request text."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from review_assistant.log import fields, get_logger
from review_assistant.models import Reply, Request

log = get_logger("provider")


class MissingFixtureError(LookupError):
    """No recorded reply exists for this request text."""


def request_key(text: str) -> str:
    """Compute the fixture name for a request: the hex SHA-256 of its text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MockProvider:
    """A provider that never calls a model: it looks the request up in the fixtures folder."""

    name = "mock"

    def __init__(self, replies_dir: str | Path = "fixtures/replies") -> None:
        """Point the mock at a folder of recorded replies."""
        self.replies_dir = Path(replies_dir)
        self.call_log: list[Request] = []

    def complete(self, request: Request) -> Reply:
        """Return the recorded reply for this request, or raise with the key that is missing."""
        self.call_log.append(request)
        key = request_key(request.text)
        file = self.replies_dir / f"{key}.json"
        if not file.exists():
            first_line = request.text.splitlines()[0] if request.text else ""
            raise MissingFixtureError(
                f"no recorded reply {key} for request about {request.path!r} ({first_line[:60]!r}); "
                f"record one with scripts/make_fixtures.py"
            )
        data = json.loads(file.read_text(encoding="utf-8"))
        reply = Reply(
            content=str(data["content"]),
            input_tokens=int(data["input_tokens"]),
            output_tokens=int(data["output_tokens"]),
            model=str(data.get("model", request.model)),
        )
        log.info(
            "ok          %s",
            fields(path=request.path, input=reply.input_tokens, output=reply.output_tokens),
        )
        return reply
