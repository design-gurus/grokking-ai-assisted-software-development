"""Decide which findings are kept: the severity floor, and the line being in the diff."""

from __future__ import annotations

from fnmatch import fnmatch

from review_assistant.models import FileDiff, Finding

ORDER = ["low", "medium", "high", "critical"]


def meets_floor(severity: str, floor: str) -> bool:
    """Decide whether a severity is at or above the floor; an unknown severity never is."""
    if severity not in ORDER or floor not in ORDER:
        return False
    return ORDER.index(severity) >= ORDER.index(floor)


def apply_floor(findings: list[Finding], floor: str) -> list[Finding]:
    """Keep the findings at or above the floor, in the order they arrived, nothing else changed."""
    return [finding for finding in findings if meets_floor(finding.severity, floor)]


def is_ignored(path: str, patterns: list[str]) -> bool:
    """Decide whether a path matches any ignore pattern."""
    return any(fnmatch(path, pattern) for pattern in patterns)


def apply_filters(findings: list[Finding], floor: str, ignore_paths: list[str]) -> list[Finding]:
    """Drop ignored paths first, then findings below the floor. Order is preserved."""
    kept = [f for f in findings if not is_ignored(f.path, ignore_paths)]
    return apply_floor(kept, floor)


def in_diff(findings: list[Finding], file: FileDiff) -> list[Finding]:
    """Drop any finding whose line is not a line the diff shows for this file.

    The model is asked to cite lines from the diff. One that does not is either a hallucinated
    line or a finding about text that was never part of the change, and neither gets posted.
    """
    allowed = file.new_lines()
    return [finding for finding in findings if finding.path == file.path and finding.line in allowed]
