"""What every lab check shares: git helpers, the result list, and the skip rule.

A check prints one line per criterion, green or red, and exits non-zero if any criterion is red.
When the lab's folder is absent the check prints SKIPPED and exits zero, so the job is green on
pull requests that are not that lab.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS: list[tuple[bool, str]] = []


def git(*args: str, check: bool = True) -> str:
    """Run git in the repository and return stdout."""
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command and return the completed process without raising."""
    merged = {**os.environ, **(env or {})}
    return subprocess.run(list(args), cwd=cwd or ROOT, capture_output=True, text=True, env=merged, check=False)


def base_sha() -> str:
    """The commit the pull request is against: BASE_SHA from the workflow, else origin/main."""
    sha = os.environ.get("BASE_SHA", "").strip()
    if sha:
        return sha
    for ref in ("origin/main", "main"):
        if git("rev-parse", "--verify", "--quiet", ref, check=False):
            return git("merge-base", ref, "HEAD")
    return git("rev-list", "--max-parents=0", "HEAD").splitlines()[-1]


def head_sha() -> str:
    """The commit under test."""
    return os.environ.get("HEAD_SHA", "").strip() or git("rev-parse", "HEAD")


def commits_between(base: str, head: str) -> list[str]:
    """The commits on the branch, oldest first."""
    out = git("rev-list", "--reverse", f"{base}..{head}")
    return out.splitlines() if out else []


def commit_message(sha: str) -> str:
    """The full commit message."""
    return git("log", "-1", "--format=%B", sha)


def first_commit_touching(path: str, base: str, head: str) -> str | None:
    """The oldest commit on the branch that touches the path, or None."""
    out = git("log", "--reverse", "--format=%H", f"{base}..{head}", "--", path)
    return out.splitlines()[0] if out else None


def commit_index(sha: str | None, order: list[str]) -> int:
    """Where a commit sits on the branch; a missing commit sorts after everything."""
    return order.index(sha) if sha in order else len(order) + 1


def file_at(sha: str, path: str) -> str | None:
    """A file's text at a commit, or None when it does not exist there."""
    done = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=ROOT, capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else None


def changed_paths(base: str, head: str, prefix: str = "") -> list[str]:
    """Paths changed on the branch, optionally under a prefix."""
    out = git("diff", "--name-only", base, head)
    return [p for p in out.splitlines() if p.startswith(prefix)]


def numstat(base: str, head: str, prefix: str) -> tuple[int, int]:
    """Lines changed and files changed under a prefix, between two commits."""
    out = git("diff", "--numstat", base, head, "--", prefix)
    lines = 0
    files = 0
    for row in out.splitlines():
        added, deleted, _ = row.split("\t", 2)
        if added == "-":
            continue
        lines += int(added) + int(deleted)
        files += 1
    return lines, files


def sections(markdown: str, level: str = "## ") -> dict[str, str]:
    """Split a markdown file into {heading: body} at one heading level."""
    found: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    for line in markdown.splitlines():
        if line.startswith(level):
            if current is not None:
                found[current] = "\n".join(body).strip()
            current = line[len(level) :].strip()
            body = []
        else:
            body.append(line)
    if current is not None:
        found[current] = "\n".join(body).strip()
    return found


def bullets(body: str) -> list[str]:
    """Top-level bullets in a body, with wrapped continuation lines joined."""
    items: list[str] = []
    for line in body.splitlines():
        if re.match(r"^- ", line):
            items.append(line[2:].strip())
        elif items and line.startswith("  ") and line.strip():
            items[-1] += " " + line.strip()
    return items


def check(ok: bool, what: str) -> bool:
    """Record one criterion."""
    RESULTS.append((ok, what))
    print(("GREEN " if ok else "RED   ") + what)
    return ok


def skip(lab: str, reason: str) -> None:
    """Leave the job green when the lab has not been started on this branch."""
    print(f"SKIPPED {lab}: {reason}")
    sys.exit(0)


def finish(lab: str) -> None:
    """Exit non-zero when any criterion is red."""
    red = [what for ok, what in RESULTS if not ok]
    print(f"\n{lab}: {len(RESULTS) - len(red)} green, {len(red)} red")
    sys.exit(1 if red else 0)
