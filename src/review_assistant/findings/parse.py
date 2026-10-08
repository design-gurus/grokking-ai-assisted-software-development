"""Turn a provider's reply into findings."""

from __future__ import annotations

import json
import re

from review_assistant.findings.filter import ORDER
from review_assistant.models import Finding

_FENCE = re.compile(r"^```[a-z]*\n|\n```$", re.MULTILINE)


class ReplyFormatError(ValueError):
    """The reply did not hold a JSON array of findings."""


def parse_reply(content: str, path: str) -> list[Finding]:
    """Read the JSON array out of a reply and return one Finding per well-formed item.

    Items missing a field, with a line that is not a positive integer or a severity outside the
    four levels are skipped rather than raised, because one bad item should not lose the others.
    A reply that is not a JSON array at all raises ReplyFormatError.
    """
    stripped = _FENCE.sub("", content.strip()).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise ReplyFormatError(f"reply for {path} is not JSON: {error.msg}") from error
    if not isinstance(data, list):
        raise ReplyFormatError(f"reply for {path} is not a JSON array")
    findings: list[Finding] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        line = item.get("line")
        severity = item.get("severity")
        message = item.get("message")
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            continue
        if not isinstance(severity, str) or severity not in ORDER:
            continue
        if not isinstance(message, str) or not message.strip():
            continue
        findings.append(Finding(path=path, line=line, severity=severity, message=message.strip()))
    return findings
