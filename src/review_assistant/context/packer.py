"""Choose which changed files go into a provider request, within a token budget."""

from __future__ import annotations

from dataclasses import dataclass, field

from review_assistant.models import FileDiff


@dataclass
class Pack:
    """The files that fit, in order, and the ones that were dropped."""

    files: list[FileDiff] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    tokens: int = 0


def estimate_tokens(text: str) -> int:
    """Rough token count: about four characters per token."""
    return max(1, len(text) // 4)


def pack(files: list[FileDiff], model_limit: int, reserved_for_reply: int) -> Pack:
    """Keep files in the given order while they fit; drop the rest once one does not.

    The budget is model_limit minus reserved_for_reply. Files are never reordered,
    because the caller already sorted them by how much of the diff they carry, so
    the first file that does not fit ends the pack and every file after it is dropped.
    """
    budget = model_limit - reserved_for_reply
    result = Pack()
    for i, f in enumerate(files):
        cost = estimate_tokens(f.patch) + estimate_tokens(f.neighbors)
        if result.tokens + cost > budget:
            result.dropped.extend(g.path for g in files[i:])
            break
        result.files.append(f)
        result.tokens += cost
    return result
