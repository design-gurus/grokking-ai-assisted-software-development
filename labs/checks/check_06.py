"""Lab 6, spot the bug: the right defects in the right places on the five review branches, and nothing else."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, check, finish, skip  # noqa: E402

LAB = "labs/check-06"
BRANCHES = ["review-a", "review-b", "review-c", "review-d", "review-e"]
# branch -> (sha256 of the planted file's path, first line, last line) or None for the clean branch.
PLANTED: dict[str, tuple[str, int, int] | None] = {'review-a': ('425a4054cfd576ff59b39252a3d2e25381a566af0d6312b5780f4ae42bd9768c', 1, 90), 'review-b': ('b2e11d4ce3a787bc09596dc663ff93eb1f7641d16b0cd998a5d676e8ddc818db', 35, 39), 'review-c': ('50c86b7ed8ac2cf95bd48334961bf0530cdc77b5a56f852c5c61b89d735fd711', 23, 24), 'review-d': None, 'review-e': ('9c16c59752ea56341c4cbab1ec6c2f2739c955249216bce1357e9297c0a46010', 39, 41)}
SEVERITIES = {"low", "medium", "high", "critical"}
DEFECT = re.compile(r"^- DEFECT:\s*(?P<path>[^\s#]+)(?:#\S+)?\s+line\s+(?P<line>\d+)\b.*?SEVERITY:\s*(?P<severity>\w+)", re.IGNORECASE)


def main() -> None:
    notes_dir = ROOT / "labs" / "06"
    if not notes_dir.exists():
        skip(LAB, "labs/06/ is absent")
    for branch in BRANCHES:
        file = notes_dir / f"{branch}.md"
        if not check(file.exists(), f"labs/06/{branch}.md exists"):
            continue
        lines = file.read_text(encoding="utf-8").splitlines()
        defects = [DEFECT.match(ln) for ln in lines if ln.startswith("- DEFECT:")]
        clean = [ln for ln in lines if ln.startswith("- CLEAN:")]
        malformed = [ln for ln in lines if ln.startswith("- DEFECT:") and not DEFECT.match(ln)]
        check(not malformed, f"{branch}: every DEFECT line has a path, a line number and a SEVERITY ({len(malformed)} malformed)")
        planted = PLANTED[branch]
        if planted is None:
            check(not defects, f"{branch}: the clean branch has no DEFECT line ({len(defects)} found)")
            check(len(clean) == 1, f"{branch}: the clean branch has one CLEAN line")
            continue
        digest, lo, hi = planted
        hits = [m for m in defects if m and hashlib.sha256(m.group("path").encode()).hexdigest() == digest and lo <= int(m.group("line")) <= hi]
        misses = [m for m in defects if m and m not in hits]
        check(bool(hits), f"{branch}: a DEFECT line names the planted file and a line within the planted hunk")
        check(not misses, f"{branch}: no DEFECT line names another file or a line outside the planted hunk ({len(misses)} false positives)")
        check(all(m.group("severity").lower() in SEVERITIES for m in defects if m), f"{branch}: every SEVERITY is one of the four levels")
    finish(LAB)


if __name__ == "__main__":
    main()
