"""Parse a unified diff into files and hunks.

Hand written, early, in an afternoon. It handles what the fixtures and the course's pull requests
contain: renamed files, deleted files, binary markers, the no-newline marker, hunk headers with
and without counts. It has no tests by design: it is the legacy module the course refactors.
"""

from __future__ import annotations

import re

from review_assistant.models import FileDiff, Hunk

# don't ask
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
_GIT_HEADER = re.compile(r"^diff --git a/(.*?) b/(.*)$")
_RENAME_FROM = re.compile(r"^rename from (.*)$")
_RENAME_TO = re.compile(r"^rename to (.*)$")
_NEW_PATH = re.compile(r"^\+\+\+ (?:b/)?(.*)$")
_OLD_PATH = re.compile(r"^--- (?:a/)?(.*)$")


def parse(text: str) -> list[FileDiff]:
    """Turn the text of a unified diff into one FileDiff per changed file, in order."""
    files: list[FileDiff] = []
    current: FileDiff | None = None
    hunk: Hunk | None = None
    chunk: list[str] = []

    def close_file() -> None:
        nonlocal current, hunk, chunk
        if current is not None:
            current.patch = "\n".join(chunk).rstrip("\n") + "\n"
            current.neighbors = _neighbors(current)
            files.append(current)
        current = None
        hunk = None
        chunk = []

    for raw in text.replace("\r\n", "\n").split("\n"):
        git = _GIT_HEADER.match(raw)
        if git:
            close_file()
            current = FileDiff(path=git.group(2), patch="", old_path=git.group(1))
            chunk = [raw]
            continue
        if current is None:
            # Lines before the first file header, or a diff with no git header at all.
            if _OLD_PATH.match(raw):
                current = FileDiff(path="", patch="")
                chunk = [raw]
            continue
        chunk.append(raw)
        if raw.startswith("Binary files"):
            current.is_binary = True
            continue
        if raw.startswith("deleted file mode"):
            current.is_deleted = True
            continue
        rename_from = _RENAME_FROM.match(raw)
        if rename_from:
            current.old_path = rename_from.group(1)
            continue
        rename_to = _RENAME_TO.match(raw)
        if rename_to:
            current.path = rename_to.group(1)
            continue
        if raw.startswith("--- "):
            old = _OLD_PATH.match(raw)
            if old and old.group(1) != "/dev/null" and not current.old_path:
                current.old_path = old.group(1)
            continue
        if raw.startswith("+++ "):
            new = _NEW_PATH.match(raw)
            if new and new.group(1) != "/dev/null":
                current.path = new.group(1)
            continue
        header = _HUNK.match(raw)
        if header:
            hunk = Hunk(
                old_start=int(header.group(1)),
                old_count=int(header.group(2)) if header.group(2) is not None else 1,
                new_start=int(header.group(3)),
                new_count=int(header.group(4)) if header.group(4) is not None else 1,
                section=header.group(5).strip(),
            )
            current.hunks.append(hunk)
            continue
        if hunk is None:
            continue
        if raw.startswith("\\"):
            # "\ No newline at end of file" belongs to the previous line, not to the hunk's count.
            continue
        if raw == "" and _hunk_is_full(hunk):
            hunk = None
            continue
        if raw[:1] in (" ", "+", "-"):
            hunk.lines.append(raw)
        elif raw == "":
            hunk.lines.append(" ")
    close_file()
    return files


def _hunk_is_full(hunk: Hunk) -> bool:
    kinds = hunk.kinds()
    old = sum(1 for k in kinds if k in (" ", "-"))
    new = sum(1 for k in kinds if k in (" ", "+"))
    return old >= hunk.old_count and new >= hunk.new_count


def _neighbors(file: FileDiff) -> str:
    """Collect the unchanged lines around the hunks: in command line mode, the context lines."""
    lines: list[str] = []
    for hunk in file.hunks:
        for line in hunk.lines:
            if line.startswith(" "):
                lines.append(line[1:])
    return "\n".join(lines)
