"""Map the lines of a hunk to line numbers in the new file."""

from __future__ import annotations


def new_file_lines(new_start: int, kinds: list[str]) -> list[int]:
    """For each hunk line, its line number in the new file, or -1 for a removed line.

    `new_start` is the number after the plus sign in the hunk header. Context lines and added
    lines each take the next number; removed lines take none, because they are not in the new file.
    """
    numbers: list[int] = []
    line = new_start
    for kind in kinds:
        if kind == "-":
            numbers.append(-1)
            continue
        numbers.append(line)
        line += 1
    return numbers
