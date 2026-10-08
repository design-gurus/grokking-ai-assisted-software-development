"""The data types every module shares: diffs, findings, requests, replies and pull requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Hunk:
    """One hunk of a unified diff: the header numbers and the lines with their prefix character."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str] = field(default_factory=list)
    section: str = ""

    def kinds(self) -> list[str]:
        """List the prefix character of each line: a space, a plus or a minus."""
        return [(line[:1] or " ") for line in self.lines]

    def header(self) -> str:
        """Render the hunk header in canonical form, both counts written, no section heading."""
        return f"@@ -{self.old_start},{self.old_count} +{self.new_start},{self.new_count} @@"


@dataclass
class FileDiff:
    """One changed file: its path, the patch text for that file, its hunks and the lines around them."""

    path: str
    patch: str
    hunks: list[Hunk] = field(default_factory=list)
    neighbors: str = ""
    old_path: str | None = None
    is_binary: bool = False
    is_deleted: bool = False

    def new_lines(self) -> set[int]:
        """Every line number in the new file that this diff touches or shows."""
        from review_assistant.diff.lines import new_file_lines

        numbers: set[int] = set()
        for hunk in self.hunks:
            numbers.update(n for n in new_file_lines(hunk.new_start, hunk.kinds()) if n > 0)
        return numbers


@dataclass
class Finding:
    """One review finding: a path, a line in the new file, a severity and a message."""

    path: str
    line: int
    severity: str
    message: str


@dataclass
class Request:
    """One request to a provider: the text the model reads, the model, and the file it is about.

    `headers` is filled in by the provider that sends the request. `untrusted` carries text that
    came from outside the repository, rendered as data and never as instructions.
    """

    text: str
    model: str
    path: str
    untrusted: dict[str, str] | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Render the request as plain data, for logging and for the mock's call log."""
        return {"text": self.text, "model": self.model, "path": self.path, "untrusted": self.untrusted}


@dataclass
class Reply:
    """What a provider returned: the content and the token counts the ledger bills."""

    content: str
    input_tokens: int
    output_tokens: int
    model: str


@dataclass
class PullRequest:
    """The parts of a pull request the service reads."""

    repo: str
    number: int
    head_sha: str
    base_sha: str
    title: str = ""
    description: str = ""
    author: str = ""


@dataclass
class Job:
    """One unit of work for the worker: a pull request and the webhook delivery that carried it."""

    pull_request: PullRequest
    delivery: str
    installation: int = 0
    updated_at: datetime | None = None
