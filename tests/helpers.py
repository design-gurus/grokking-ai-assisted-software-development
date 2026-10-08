"""Paths and small helpers the tests share."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / "fixtures" / "patches"
REPLIES = ROOT / "fixtures" / "replies"


def patch_text(name: str) -> str:
    """The text of one fixture patch."""
    return (PATCHES / name).read_text(encoding="utf-8")
