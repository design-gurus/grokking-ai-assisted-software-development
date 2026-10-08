"""Render one changed file into the text a provider reads."""

from __future__ import annotations

from review_assistant.models import FileDiff, PullRequest, Request

INSTRUCTIONS = """You are reviewing one file from a pull request.
Report defects only: bugs, security problems, and behavior that disagrees with the surrounding code.
Do not report style. Do not summarize the change.
Reply with a JSON array and nothing else. Each item has:
  "line": a line number in the new file, taken from the diff below,
  "severity": one of "low", "medium", "high", "critical",
  "message": one sentence a reviewer could post as a comment.
Reply with [] when there is nothing to report."""


def render_file(file: FileDiff) -> str:
    """Render the diff of one file with the unchanged lines around its hunks, as the model sees it."""
    parts = [f"File: {file.path}", "", "```diff", file.patch.rstrip("\n"), "```"]
    if file.neighbors:
        parts += ["", "Surrounding lines:", "", "```", file.neighbors, "```"]
    return "\n".join(parts)


def build_request(
    file: FileDiff,
    model: str,
    template_version: int = 1,
    pr: PullRequest | None = None,
) -> Request:
    """Build the request for one file.

    Template version one is the instructions, the author's context from the pull request
    description when there is one, a blank line, and the rendered file.
    """
    if template_version != 1:
        raise ValueError(f"request template version {template_version} is not implemented")
    text = INSTRUCTIONS
    if pr is not None and pr.description.strip():
        text += "\n\nContext from the author:\n" + pr.description.strip()
    text += "\n\n" + render_file(file)
    return Request(text=text, model=model, path=file.path)
