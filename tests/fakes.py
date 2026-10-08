"""Test doubles: a GitHub client that serves a diff from memory and refuses lines outside it."""

from __future__ import annotations

from dataclasses import dataclass, field

from review_assistant.diff.parser import parse
from review_assistant.models import PullRequest
from review_assistant.web.github import FileContents, GitHubError


@dataclass
class FakeGitHub:
    """A GitHub that holds one pull request, its diff, and the files behind it."""

    pr: PullRequest
    diff_text: str
    files: dict[str, str] = field(default_factory=dict)
    comments: list[tuple[int, str, int, str]] = field(default_factory=list)
    file_fetches: list[tuple[str, str]] = field(default_factory=list)
    diff_fetches: int = 0

    def pull_request(self, repo: str, number: int) -> PullRequest:
        return self.pr

    def diff(self, repo: str, number: int) -> str:
        self.diff_fetches += 1
        return self.diff_text

    def get_file(self, repo: str, path: str, ref: str) -> FileContents:
        self.file_fetches.append((path, ref))
        if path in self.files:
            return FileContents(path=path, ref=ref, text=self.files[path])
        return FileContents.synthetic(path, ref)

    def post_review_comment(
        self, repo: str, number: int, commit_id: str, path: str, line: int, body: str
    ) -> int:
        allowed = {f.path: f.new_lines() for f in parse(self.diff_text)}
        if path not in allowed or line not in allowed[path]:
            raise GitHubError(f"422 Unprocessable: line {line} is not part of the diff for {path}")
        self.comments.append((number, path, line, body))
        return len(self.comments)
