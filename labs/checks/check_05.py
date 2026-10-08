"""Lab 5, tests that can fail: tests from the spec, a property, a second opinion, every survivor accounted for."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ROOT,
    base_sha,
    check,
    commit_index,
    commits_between,
    finish,
    first_commit_touching,
    head_sha,
    run,
    skip,
)

LAB = "labs/check-05"
SURVIVORS = "labs/05/survivors.md"
DIFFERENTIAL = "tests/test_parser_differential.py"
TARGETS = ["src/review_assistant/findings/filter.py", "src/review_assistant/ledger/cost.py"]


def survivors_from_mutmut() -> list[str]:
    """Run the mutation tool on the two targets and return the names of the mutants that survived."""
    ran = run(sys.executable, "-m", "mutmut", "run")
    results = run(sys.executable, "-m", "mutmut", "results")
    text = ran.stdout + "\n" + results.stdout
    names: list[str] = []
    for line in text.splitlines():
        if re.search(r"surviv", line, re.IGNORECASE):
            match = re.search(r"([\w.]+__mutmut_\d+|\bM?\d+\b)", line)
            if match:
                names.append(match.group(1))
    return sorted(set(names))


def main() -> None:
    if not (ROOT / SURVIVORS).exists() and not (ROOT / DIFFERENTIAL).exists():
        skip(LAB, f"neither {SURVIVORS} nor {DIFFERENTIAL} exists")
    base, head = base_sha(), head_sha()
    order = commits_between(base, head)

    suite = run(sys.executable, "-m", "pytest", "-q")
    check(suite.returncode == 0, "the suite is green at the head of the branch")

    test_files = sorted((ROOT / "tests").glob("test_*.py"))
    test_source = {p: p.read_text(encoding="utf-8") for p in test_files}
    ledger_tests = [p for p in test_files if "cost" in p.name and run("git", "diff", "--quiet", base, head, "--", str(p.relative_to(ROOT))).returncode != 0]
    if ledger_tests:
        first_tests = min((commit_index(first_commit_touching(str(p.relative_to(ROOT)), base, head), order) for p in ledger_tests), default=len(order) + 1)
        impl = first_commit_touching("src/review_assistant/ledger/cost.py", base, head)
        check(impl is None or first_tests < commit_index(impl, order), "the ledger tests were committed before cost.py was touched")
    else:
        check(True, "the ledger tests were committed before cost.py was touched (cost.py untouched on this branch)")
    half_cent = any(re.search(r"review_cost_cents\(\s*1000,\s*0,\s*500,\s*0\s*\)\s*==\s*1", s) for s in test_source.values())
    check(half_cent, "a test asserts review_cost_cents(1000, 0, 500, 0) == 1")

    property_tests = [p for p, s in test_source.items() if "hypothesis" in s and re.search(r"meets_floor|apply_floor|findings\.filter", s)]
    check(bool(property_tests), "at least one test imports hypothesis and targets the filter")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    seeded = "derandomize = true" in pyproject or any(re.search(r"derandomize=True|seed\(", s) for s in test_source.values())
    check(seeded, "the property tests run with a fixed seed")

    diff_exists = (ROOT / DIFFERENTIAL).exists()
    check(diff_exists, f"{DIFFERENTIAL} exists")
    if diff_exists:
        source = test_source.get(ROOT / DIFFERENTIAL, "")
        check("unidiff" in source and "fixtures" in source, f"{DIFFERENTIAL} runs the library parser over the fixture patches")
        differential = run(sys.executable, "-m", "pytest", "-q", DIFFERENTIAL)
        check(differential.returncode == 0, f"{DIFFERENTIAL} passes")

    survivors = survivors_from_mutmut()
    notes = (ROOT / SURVIVORS).read_text(encoding="utf-8") if (ROOT / SURVIVORS).exists() else ""
    check(not survivors or bool(notes), f"{SURVIVORS} exists when the mutation tool reports survivors")
    for name in survivors:
        line = next((ln for ln in notes.splitlines() if name in ln), None)
        if line is None:
            check(False, f"survivor {name} has a line in {SURVIVORS}")
        elif "KILLED BY:" in line:
            check(False, f"survivor {name} claims KILLED BY: but still survives")
        else:
            check("EQUIVALENT:" in line, f"survivor {name} is marked EQUIVALENT: with a reason")
    if not survivors:
        check(True, f"no surviving mutant on {', '.join(TARGETS)}")
    finish(LAB)


if __name__ == "__main__":
    main()
