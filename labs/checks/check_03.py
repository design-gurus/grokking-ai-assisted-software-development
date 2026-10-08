"""Lab 3, add ignore paths: the spec came first, the plan has checks, the diff is small and clean."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ROOT,
    base_sha,
    bullets,
    check,
    commit_index,
    commits_between,
    file_at,
    finish,
    first_commit_touching,
    head_sha,
    numstat,
    run,
    sections,
    skip,
)

LAB = "labs/check-03"
SPEC = "labs/03/spec.md"
PLAN = "labs/03/plan.md"
HEADINGS = ["Goal", "Acceptance examples", "Constraints", "Non-goals"]


def public_functions_without_docstrings(source: str) -> list[str]:
    tree = ast.parse(source)
    missing: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_"):
            if ast.get_docstring(node) is None:
                missing.append(node.name)
    return missing


def main() -> None:
    if not (ROOT / SPEC).exists():
        skip(LAB, f"{SPEC} is absent")
    base, head = base_sha(), head_sha()
    order = commits_between(base, head)

    spec = sections((ROOT / SPEC).read_text(encoding="utf-8"))
    check(all(h in spec for h in HEADINGS), f"{SPEC} has the four headings: {', '.join(HEADINGS)}")
    examples = bullets(spec.get("Acceptance examples", ""))
    check(len(examples) >= 3, f"{SPEC} holds at least three acceptance examples ({len(examples)} found)")

    spec_first = first_commit_touching(SPEC, base, head)
    src_first = first_commit_touching("src/", base, head)
    check(
        spec_first is not None and commit_index(spec_first, order) < commit_index(src_first, order),
        "the spec's first commit is earlier than the first commit touching src/",
    )

    plan_text = (ROOT / PLAN).read_text(encoding="utf-8") if (ROOT / PLAN).exists() else ""
    steps = bullets(plan_text)
    check(bool(steps), f"{PLAN} exists with at least one step")
    with_checks = [s for s in steps if re.search(r"check", s, re.IGNORECASE) or "~~" in s]
    check(len(with_checks) == len(steps), "every plan bullet ends with a check")
    check("~~" in plan_text or re.search(r"\bstruck\b", plan_text, re.IGNORECASE) is not None, "the struck step is named")

    lines, files = numstat(base, head, "src/")
    check(lines <= 80 and files <= 4, f"the diff under src/ is at most 80 lines across at most 4 files ({lines} lines, {files} files)")

    lint = run(sys.executable, "-m", "ruff", "check", ".")
    check(lint.returncode == 0, "ruff passes" + ("" if lint.returncode == 0 else f": {lint.stdout[-400:]}"))
    types = run(sys.executable, "-m", "mypy")
    check(types.returncode == 0, "mypy passes" + ("" if types.returncode == 0 else f": {types.stdout[-400:]}"))

    missing: list[str] = []
    for path in [p for p in run("git", "diff", "--name-only", base, head, "--", "src/").stdout.split() if p.endswith(".py")]:
        before = file_at(base, path) or ""
        after = file_at(head, path) or ""
        was = set(public_functions_without_docstrings(before)) if before else set()
        now = set(public_functions_without_docstrings(after)) if after else set()
        missing += [f"{path}:{name}" for name in sorted(now - was)]
    check(not missing, "every new public function has a docstring" + ("" if not missing else f" (missing: {', '.join(missing)})"))

    cost_tests = run("git", "diff", "--quiet", base, head, "--", "tests/test_cost.py")
    check(cost_tests.returncode == 0, "the ledger tests pass unchanged (tests/test_cost.py untouched)")
    tests = run(sys.executable, "-m", "pytest", "-q", "tests/test_cost.py")
    check(tests.returncode == 0, "the ledger tests are green")
    replies = run("git", "diff", "--quiet", base, head, "--", "fixtures/replies/")
    check(replies.returncode == 0, "no file under fixtures/replies/ was modified")
    finish(LAB)


if __name__ == "__main__":
    main()
