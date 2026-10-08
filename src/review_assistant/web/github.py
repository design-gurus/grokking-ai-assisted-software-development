"""The GitHub client: the pull request, its diff, file contents, and posting review comments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx

from review_assistant.log import fields, get_logger
from review_assistant.models import Hunk, PullRequest

log = get_logger("github")
API = "https://api.github.com"


class GitHubError(RuntimeError):
    """GitHub refused a call; the message carries the status and what it refused."""


@dataclass
class FileContents:
    """The full text of one file at one ref, with a helper for the lines around a hunk."""

    path: str
    ref: str
    text: str

    def lines_around(self, hunk: Hunk, context: int = 3) -> str:
        """Take the unchanged lines just before and after a hunk, from the file as it is at the ref."""
        lines = self.text.split("\n")
        start = max(0, hunk.new_start - 1 - context)
        end = min(len(lines), hunk.new_start - 1 + hunk.new_count + context)
        return "\n".join(lines[start:end])

    @classmethod
    def synthetic(cls, path: str, ref: str, length: int = 240) -> FileContents:
        """Make a placeholder file of numbered lines, for tests and for recording fixtures."""
        return cls(path=path, ref=ref, text="\n".join(f"line {n}" for n in range(1, length + 1)))


class GitHubApi(Protocol):
    """What the worker needs from GitHub; the real client and the test fake both provide it."""

    def pull_request(self, repo: str, number: int) -> PullRequest:
        """Fetch the pull request's metadata."""
        ...

    def diff(self, repo: str, number: int) -> str:
        """Fetch the pull request's unified diff."""
        ...

    def get_file(self, repo: str, path: str, ref: str) -> FileContents:
        """One file's contents at a ref."""
        ...

    def post_review_comment(
        self, repo: str, number: int, commit_id: str, path: str, line: int, body: str
    ) -> int:
        """Post a comment on a line of the diff and return the comment id."""
        ...


@dataclass
class GitHubClient:
    """The real client, over the REST API with a token."""

    token: str
    base_url: str = API
    timeout: float = 30.0
    _http: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Open the HTTP client with the token and the API headers."""
        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    def pull_request(self, repo: str, number: int) -> PullRequest:
        """Fetch the pull request's metadata."""
        response = self._http.get(f"/repos/{repo}/pulls/{number}")
        _raise_for(response, f"pull request {number}")
        data = response.json()
        return PullRequest(
            repo=repo,
            number=number,
            head_sha=str(data["head"]["sha"]),
            base_sha=str(data["base"]["sha"]),
            title=str(data.get("title") or ""),
            description=str(data.get("body") or ""),
            author=str((data.get("user") or {}).get("login") or ""),
        )

    def diff(self, repo: str, number: int) -> str:
        """Fetch the pull request's diff as text."""
        response = self._http.get(
            f"/repos/{repo}/pulls/{number}", headers={"Accept": "application/vnd.github.diff"}
        )
        _raise_for(response, f"diff of pull request {number}")
        log.info("fetch diff  %s", fields(pr=number))
        return response.text

    def get_file(self, repo: str, path: str, ref: str) -> FileContents:
        """Fetch one file's contents at a ref."""
        response = self._http.get(
            f"/repos/{repo}/contents/{path}",
            params={"ref": ref},
            headers={"Accept": "application/vnd.github.raw+json"},
        )
        _raise_for(response, f"{path} at {ref}")
        log.info("fetch file  %s", fields(path=path, ref=ref[:7]))
        return FileContents(path=path, ref=ref, text=response.text)

    def post_review_comment(
        self, repo: str, number: int, commit_id: str, path: str, line: int, body: str
    ) -> int:
        """Post one review comment on a line of the new file.

        GitHub refuses a line that is not part of the diff with a 422, and the service surfaces
        that as a GitHubError naming the line and the path, because it means a finding's line
        number was wrong, not that GitHub is down.
        """
        response = self._http.post(
            f"/repos/{repo}/pulls/{number}/comments",
            json={"body": body, "commit_id": commit_id, "path": path, "line": line, "side": "RIGHT"},
        )
        if response.status_code == 422:
            raise GitHubError(f"422 Unprocessable: line {line} is not part of the diff for {path}")
        _raise_for(response, f"comment on {path}:{line}")
        return int(response.json()["id"])


def _raise_for(response: httpx.Response, what: str) -> None:
    if response.status_code >= 400:
        raise GitHubError(f"{response.status_code} on {what}: {response.text[:200]}")
