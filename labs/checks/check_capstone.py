"""The capstone: the gate is green, and the verification record is committed beside the change."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, base_sha, check, commits_between, finish, head_sha, run, skip  # noqa: E402

LAB = "labs/check-capstone"
RECORD = "capstone/verification.md"


def main() -> None:
    if not (ROOT / RECORD).exists():
        skip(LAB, f"{RECORD} is absent")
    base, head = base_sha(), head_sha()
    for tool in (["ruff", "check", "."], ["mypy"], ["pytest", "-q"]):
        done = run(sys.executable, "-m", *tool)
        check(done.returncode == 0, f"{tool[0]} is green" + ("" if done.returncode == 0 else f": {(done.stdout or done.stderr)[-300:]}"))
    record = (ROOT / RECORD).read_text(encoding="utf-8")
    for line in ("Spec:", "Tests written first:", "Hypotheses:", "Mutation:", "Read:", "Not read:", "Risk:"):
        check(line in record, f"{RECORD} has a {line} line")
    hashes = set(re.findall(r"\b[0-9a-f]{7,40}\b", record))
    known = set(commits_between(base, head)) | {base, head}
    real = [h for h in hashes if any(k.startswith(h) for k in known) or run("git", "cat-file", "-e", f"{h}^{{commit}}").returncode == 0]
    check(bool(hashes) and len(real) == len(hashes), f"every hash in {RECORD} is a commit ({len(real)}/{len(hashes)})")
    test_source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "tests").glob("test_*.py"))
    names = set(re.findall(r"(test_\w+)", record))
    missing = [n for n in names if not re.search(rf"def {n}\(", test_source)]
    check(bool(names) and not missing, f"every test named in {RECORD} exists" + ("" if not missing else f" (missing: {', '.join(missing)})"))
    for artifact in ("capstone/map.md", "capstone/spec.md", "capstone/plan.md", "capstone/hypotheses.md", "capstone/mutation.md", "capstone/review.md"):
        check((ROOT / artifact).exists(), f"{artifact} is committed")
    finish(LAB)


if __name__ == "__main__":
    main()
