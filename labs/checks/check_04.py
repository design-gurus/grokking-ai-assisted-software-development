"""Lab 4, five bugs: reproduction before the assistant, hypothesis before the fix, fixes seen to fail."""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ROOT,
    bullets,
    check,
    commit_index,
    commit_message,
    file_at,
    finish,
    git,
    head_sha,
    run,
    sections,
    skip,
)

LAB = "labs/check-04"
REPRO = "labs/04/repro.md"
HYPOTHESES = "labs/04/hypotheses.md"
BUGS = ["B1", "B2", "B3", "B4", "B5"]


def starting_commit() -> str:
    """The orphan branch's root: the bugs as planted."""
    return git("rev-list", "--max-parents=0", "HEAD").splitlines()[-1]


def branch_commits(start: str, head: str) -> list[str]:
    out = git("rev-list", "--reverse", f"{start}..{head}")
    return out.splitlines() if out else []


def fix_commits(order: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for sha in order:
        match = re.match(r"^fix (B[1-6]):", commit_message(sha).strip(), re.IGNORECASE)
        if match and match.group(1).upper() not in found:
            found[match.group(1).upper()] = sha
    return found


def worktree_at(sha: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix="lab04-start-"))
    git("worktree", "add", "--detach", str(path), sha)
    return path


def main() -> None:
    if not (ROOT / REPRO).exists() and not (ROOT / HYPOTHESES).exists():
        skip(LAB, f"neither {REPRO} nor {HYPOTHESES} exists")
    head = head_sha()
    start = starting_commit()
    order = branch_commits(start, head)
    fixes = fix_commits(order)

    repro = sections((ROOT / REPRO).read_text(encoding="utf-8")) if (ROOT / REPRO).exists() else {}
    check(bool(repro), f"{REPRO} exists with at least one ## Bn heading")
    for bug, body in repro.items():
        if not re.match(r"^B\d$", bug):
            continue
        has = all(re.search(rf"\b{field}:", body) for field in ("INPUT", "OBSERVED", "EXPECTED"))
        check(has, f"{REPRO} ## {bug} holds INPUT:, OBSERVED: and EXPECTED:")

    hyp_text = (ROOT / HYPOTHESES).read_text(encoding="utf-8") if (ROOT / HYPOTHESES).exists() else ""
    hyp = sections(hyp_text)
    check(bool(hyp), f"{HYPOTHESES} exists with at least one ## Bn heading")
    for bug, body in hyp.items():
        if not re.match(r"^B\d$", bug):
            continue
        lines = bullets(body)
        shaped = [ln for ln in lines if "PREDICTION:" in ln and "RESULT:" in ln]
        check(lines and len(shaped) == len(lines), f"{HYPOTHESES} ## {bug}: every line has PREDICTION: and RESULT: ({len(shaped)}/{len(lines)})")

    for bug, sha in fixes.items():
        if bug == "B6":
            continue
        parent_hyp = sections(file_at(f"{sha}^", HYPOTHESES) or "")
        confirmed = "RESULT: confirmed" in parent_hyp.get(bug, "")
        check(confirmed, f"fix {bug} ({sha[:7]}) lands after {HYPOTHESES} ## {bug} holds RESULT: confirmed")
        parent_repro = sections(file_at(f"{sha}^", REPRO) or "")
        check(bug in parent_repro, f"fix {bug} ({sha[:7]}) lands after {REPRO} ## {bug} was committed")
        src_before = commit_index(sha, order)
        check(src_before < len(order) + 1, f"fix {bug} is a commit on this branch")

    suite = run(sys.executable, "-m", "pytest", "-q")
    check(suite.returncode == 0, "the suite is green at the head of the branch")

    tests_dir = ROOT / "tests"
    test_source = "\n".join(p.read_text(encoding="utf-8") for p in tests_dir.glob("test_*.py"))
    start_tree = worktree_at(start)
    try:
        shutil.rmtree(start_tree / "tests", ignore_errors=True)
        shutil.copytree(tests_dir, start_tree / "tests")
        env = {"PYTHONPATH": str(start_tree / "src")}
        for bug in ("B1", "B2", "B3", "B4"):
            if bug not in fixes:
                continue
            name = f"test_repro_{bug.lower()}"
            exists = re.search(rf"def {name}\w*\(", test_source) is not None
            check(exists, f"a test named {name} exists for {bug}")
            if not exists:
                continue
            at_head = run(sys.executable, "-m", "pytest", "-q", "-k", name)
            check(at_head.returncode == 0, f"{name} is green at the head")
            at_start = run(sys.executable, "-m", "pytest", "-q", "-k", name, "-p", "no:cacheprovider", cwd=start_tree, env=env)
            check(at_start.returncode != 0, f"{name} is red at the starting commit {start[:7]}")
        if "B5" in fixes:
            existed = set(git("ls-tree", "--name-only", start, "tests/").splitlines())
            changed = [p for p in git("diff", "--name-only", start, head, "--", "tests/").splitlines() if p in existed]
            check(bool(changed), "B5: a test file that existed at the starting commit was changed")
            if changed:
                at_start = run(sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *changed, cwd=start_tree, env=env)
                check(at_start.returncode != 0, "B5: the restored test fails at the starting commit")
    finally:
        git("worktree", "remove", "--force", str(start_tree), check=False)
        shutil.rmtree(start_tree, ignore_errors=True)

    if "B6" in hyp:
        results = [ln for ln in bullets(hyp["B6"]) if "RESULT:" in ln]
        numbers = re.findall(r"\d+", " ".join(r.split("RESULT:", 1)[1] for r in results))
        check(len(numbers) >= 4, "B6: the RESULT line holds four numbers, calls and seconds before and after")
        named = re.findall(r"test_\w+", hyp["B6"])
        check(bool(named) and all(re.search(rf"def {n}\(", test_source) for n in named), "B6: the test it names exists")
    finish(LAB)


if __name__ == "__main__":
    main()
