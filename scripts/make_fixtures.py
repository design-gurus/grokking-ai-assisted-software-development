"""Write the mock provider's recorded replies for every fixture patch.

Without `--live`, the replies are the authored findings below, written in the shape a live reply
has, so the course runs with no API key. With `--live` and a key in the environment, the named
provider is called once per file and its real replies are recorded instead; the authored table is
then only the fallback for a request the live run did not cover.

Run from the repository root: python scripts/make_fixtures.py [--live anthropic|openai]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from review_assistant.config import Config
from review_assistant.context.packer import estimate_tokens
from review_assistant.context.request import build_request
from review_assistant.diff.parser import parse
from review_assistant.providers.mock import request_key
from review_assistant.web.github import FileContents

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / "fixtures" / "patches"
REPLIES = ROOT / "fixtures" / "replies"
MODEL = "mock-review-1"

# (patch file, path in the diff) -> the findings the model reported, as the JSON items it returned.
AUTHORED: dict[tuple[str, str], list[dict[str, object]]] = {
    ("001-rename-helper.patch", "src/review_assistant/web/worker.py"): [
        {
            "line": 85,
            "severity": "medium",
            "message": "Upper-casing the severity changes the text of every posted comment, which nothing in this change asked for and which downstream filters on the comment text will no longer match.",
        },
        {
            "line": 73,
            "severity": "low",
            "message": "finding.id is not a field the Finding type defines elsewhere in this file; confirm it exists or key the seen set on path and line.",
        },
    ],
    ("three-files.patch", "src/review_assistant/findings/filter.py"): [
        {
            "line": 42,
            "severity": "high",
            "message": "With strict=False every finding is returned without the path check, so a finding about another file is posted on this one.",
        },
        {
            "line": 57,
            "severity": "medium",
            "message": "The dedupe key dropped the message, so two different findings on the same line now collapse into one and the second is silently lost.",
        },
    ],
    ("three-files.patch", "src/review_assistant/cli.py"): [
        {
            "line": 18,
            "severity": "low",
            "message": "open(patch) is never closed and reads with the platform default encoding; read the file through a context manager with encoding set.",
        },
    ],
    ("three-files.patch", "src/review_assistant/config.py"): [
        {
            "line": 9,
            "severity": "critical",
            "message": "A default API key literal in source is a credential in the repository; keys come from the environment and never from a constant.",
        },
    ],
    ("003-no-newline.patch", "src/review_assistant/ledger/cost.py"): [
        {
            "line": 23,
            "severity": "high",
            "message": "Integer division truncates, so half a cent bills as zero; the docstring promises half up, which needs the 500_000 added back before dividing.",
        },
    ],
    ("004-renamed-file.patch", "src/review_assistant/web/jobs.py"): [
        {
            "line": 17,
            "severity": "high",
            "message": "appendleft on enqueue with popleft on dequeue makes the queue last in, first out; the docstring above still promises first in, first out.",
        },
    ],
    ("005-omitted-count.patch", "src/review_assistant/__init__.py"): [],
    ("005-omitted-count.patch", "VERSION"): [],
}


def reply_for(patch_name: str, path: str, request_text: str) -> dict[str, object]:
    """The authored reply for one request, in the recorded shape."""
    items = AUTHORED.get((patch_name, path), [])
    content = json.dumps(items, indent=2)
    return {
        "model": MODEL,
        "content": content,
        "input_tokens": estimate_tokens(request_text),
        "output_tokens": max(4, estimate_tokens(content)),
    }


def live_reply(provider_name: str, request_text: str, path: str) -> dict[str, object] | None:
    """Call the named live provider once and return its reply in the recorded shape."""
    from review_assistant.models import Request
    from review_assistant.providers.base import get_provider

    config = Config(provider=provider_name, model=sys.argv[3] if len(sys.argv) > 3 else "claude-sonnet-5")
    provider = get_provider(config)
    reply = provider.complete(Request(text=request_text, model=config.model, path=path))
    return {
        "model": reply.model,
        "content": reply.content,
        "input_tokens": reply.input_tokens,
        "output_tokens": reply.output_tokens,
    }


def main() -> int:
    """Write one reply file per (patch, file) request."""
    live = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--live" else None
    REPLIES.mkdir(parents=True, exist_ok=True)
    written = 0
    for patch in sorted(PATCHES.glob("*.patch")):
        for file in parse(patch.read_text(encoding="utf-8")):
            if file.is_binary or file.is_deleted or not file.hunks:
                continue
            # Two requests per file: the command line one, whose neighbors are the context lines,
            # and the worker's, whose neighbors come from the synthetic file the test fake serves.
            command_line = build_request(file, MODEL)
            file.neighbors = "\n".join(
                FileContents.synthetic(file.path, "head").lines_around(hunk) for hunk in file.hunks
            )
            worker = build_request(file, MODEL)
            for request in (command_line, worker):
                key = request_key(request.text)
                reply = live_reply(live, request.text, file.path) if live else None
                if reply is None:
                    reply = reply_for(patch.name, file.path, request.text)
                target = REPLIES / f"{key}.json"
                target.write_text(json.dumps(reply, indent=2) + "\n", encoding="utf-8")
                print(f"{patch.name:28} {file.path:48} -> {key[:12]}")
                written += 1
    print(f"wrote {written} replies to {REPLIES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
