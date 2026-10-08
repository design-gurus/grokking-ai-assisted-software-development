"""Lab 7, through the gate: a reversible migration, a flag that changes nothing by default, a real record."""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ROOT,
    base_sha,
    check,
    commit_message,
    commits_between,
    finish,
    git,
    head_sha,
    run,
    sections,
    skip,
)

LAB = "labs/check-07"
RECORD = "labs/07/verification.md"
HEADINGS = ["What was asked", "What changed, and why this shape", "What was verified, and how", "What was generated but not read", "Risk"]
REQUEST_SCRIPT = """
import hashlib, json, sys
from pathlib import Path
from review_assistant.config import Config
from review_assistant.context.request import INSTRUCTIONS, build_request
from review_assistant.diff.parser import parse
version = int(sys.argv[1])
out = {"instructions": hashlib.sha256(INSTRUCTIONS.encode()).hexdigest(), "requests": []}
for patch in sorted(Path("fixtures/patches").glob("*.patch")):
    for file in parse(patch.read_text(encoding="utf-8")):
        if file.is_binary or file.is_deleted or not file.hunks:
            continue
        request = build_request(file, "mock-review-1", version)
        out["requests"].append({"path": file.path, "sha": hashlib.sha256(request.text.encode()).hexdigest(), "untrusted": bool(request.untrusted)})
print(json.dumps(out))
"""


def requests_at(tree: Path, version: int) -> dict[str, object]:
    import json

    done = run(sys.executable, "-c", REQUEST_SCRIPT, str(version), cwd=tree, env={"PYTHONPATH": str(tree / "src")})
    if done.returncode != 0:
        return {"error": done.stderr[-400:]}
    result: dict[str, object] = json.loads(done.stdout.strip().splitlines()[-1])
    return result


def main() -> None:
    if not (ROOT / RECORD).exists():
        skip(LAB, f"{RECORD} is absent")
    base, head = base_sha(), head_sha()
    order = commits_between(base, head)

    for tool in (["ruff", "check", "."], ["mypy"], ["pytest", "-q"]):
        done = run(sys.executable, "-m", *tool)
        check(done.returncode == 0, f"{tool[0]} is green" + ("" if done.returncode == 0 else f": {(done.stdout or done.stderr)[-300:]}"))

    new_migrations = [p for p in git("diff", "--name-only", base, head, "--", "alembic/versions/").splitlines() if p.endswith(".py")]
    if new_migrations:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ledger.sqlite"
            env = {"REVIEW_LEDGER_URL": f"sqlite:///{db.as_posix()}"}
            base_rev = "0001"
            up_base = run(sys.executable, "-m", "alembic", "-x", f"url=sqlite:///{db.as_posix()}", "upgrade", base_rev, env=env)
            check(up_base.returncode == 0, f"alembic upgrade {base_rev} on a fresh database" + ("" if up_base.returncode == 0 else f": {up_base.stderr[-300:]}"))
            with sqlite3.connect(db) as conn:
                conn.execute(
                    "INSERT INTO reviews (created_at, provider, model, pull_request, delivery, input_tokens, output_tokens, cents) VALUES ('2000-01-01 00:00:00', 'mock', 'mock-review-1', 118, 'd41', 6120, 412, 3)"
                )
            up_head = run(sys.executable, "-m", "alembic", "-x", f"url=sqlite:///{db.as_posix()}", "upgrade", "head", env=env)
            check(up_head.returncode == 0, "alembic upgrade head applies the new migration")
            with sqlite3.connect(db) as conn:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(reviews)")}
                has_column = "template_version" in columns
                backfilled = has_column and conn.execute("SELECT template_version FROM reviews").fetchone()[0] == 1
            check(has_column, "reviews has a template_version column after the migration")
            check(backfilled, "the existing row carries template_version = 1 after the backfill")
            down = run(sys.executable, "-m", "alembic", "-x", f"url=sqlite:///{db.as_posix()}", "downgrade", "-1", env=env)
            check(down.returncode == 0, "alembic downgrade -1 reverts cleanly")
            with sqlite3.connect(db) as conn:
                survived = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
            check(survived, "the existing row survives the downgrade")
            up_again = run(sys.executable, "-m", "alembic", "-x", f"url=sqlite:///{db.as_posix()}", "upgrade", "head", env=env)
            check(up_again.returncode == 0, "alembic upgrade head applies again after the downgrade")
    else:
        check(True, "no new migration on this branch; the round trip is checked on the migration pull request")

    base_tree = Path(tempfile.mkdtemp(prefix="lab07-base-"))
    git("worktree", "add", "--detach", str(base_tree), base)
    try:
        at_base = requests_at(base_tree, 1)
        at_head = requests_at(ROOT, 1)
        same = "error" not in at_base and "error" not in at_head and at_base["requests"] == at_head["requests"]
        check(same, "with the flag at its default, every fixture request is byte-identical to the request before the change")
        if (ROOT / "src/review_assistant/context/request.py").read_text(encoding="utf-8") != (base_tree / "src/review_assistant/context/request.py").read_text(encoding="utf-8"):
            v2 = requests_at(ROOT, 2)
            if "error" in v2:
                check(False, f"template version two builds a request: {v2['error']}")
            else:
                every = all(bool(r["untrusted"]) for r in v2["requests"])  # type: ignore[union-attr, index]
                check(every, "with the flag at two, every request carries the untrusted field")
                check(v2["instructions"] == at_base["instructions"], "no instruction text changed")
    finally:
        git("worktree", "remove", "--force", str(base_tree), check=False)
        shutil.rmtree(base_tree, ignore_errors=True)

    body = os.environ.get("PR_BODY", "")
    heads = sections(body)
    check(all(h in heads for h in HEADINGS), "the pull request description has the five headings")
    risk = heads.get("Risk", "").strip()
    check(bool(risk) and "should be fine" not in risk.lower(), "the Risk section is non-empty and not 'should be fine'")

    record = (ROOT / RECORD).read_text(encoding="utf-8")
    hashes = set(re.findall(r"\b[0-9a-f]{7,40}\b", record))
    branch_hashes = set(order) | {base, head}
    real = [h for h in hashes if any(full.startswith(h) for full in branch_hashes) or run("git", "cat-file", "-e", f"{h}^{{commit}}").returncode == 0]
    check(bool(hashes) and len(real) == len(hashes), f"every hash in {RECORD} is a commit ({len(real)}/{len(hashes)})")
    test_source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "tests").glob("test_*.py"))
    names = set(re.findall(r"(test_\w+)", record))
    missing = [n for n in names if not re.search(rf"def {n}\(", test_source)]
    check(bool(names) and not missing, f"every test named in {RECORD} exists" + ("" if not missing else f" (missing: {', '.join(missing)})"))
    for line in ("Spec:", "Tests written first:", "Mutation:", "Not read:", "Risk:"):
        check(line in record, f"{RECORD} has a {line} line")

    bad = [sha[:7] for sha in order if not re.search(r"test|check|round trip|alembic|pytest|ruff|mypy|verif|migration", commit_message(sha), re.IGNORECASE)]
    check(not bad, "every commit message names a check" + ("" if not bad else f" (not: {', '.join(bad)})"))
    finish(LAB)


if __name__ == "__main__":
    main()
