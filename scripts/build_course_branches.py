"""Build the branches the course uses from the current base commit.

- `module-4-bugs`: an orphan branch holding the base plus the ignore-paths feature plus five
  planted bugs, squashed into one commit so there is no clean ancestor to diff against.
- `review-a` to `review-e`: five pull-request-shaped branches off the base for the review lab.

Each branch is checked with ruff, mypy and pytest before it is committed, so CI is green on all
of them. The script also writes labs/checks/check_06.py with the planted locations, hashed.

Run from the repository root on the base commit: python scripts/build_course_branches.py
It leaves you on the branch you started on.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def sh(*args: str, check: bool = True) -> str:
    done = subprocess.run(list(args), cwd=ROOT, capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        raise SystemExit(f"{' '.join(args)}\n{done.stdout}\n{done.stderr}")
    return done.stdout


def git(*args: str, check: bool = True) -> str:
    return sh("git", *args, check=check).strip()


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    for old, new in pairs:
        if old not in text:
            raise SystemExit(f"{path}: cannot find {old[:60]!r}")
        text = text.replace(old, new, 1)
    file.write_text(text, encoding="utf-8", newline="\n")


def write(path: str, text: str) -> None:
    file = ROOT / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8", newline="\n")


def verify() -> None:
    for cmd in (["ruff", "check", "."], ["mypy"], ["pytest", "-q"]):
        done = subprocess.run([PY, "-m", *cmd], cwd=ROOT, capture_output=True, text=True, check=False)
        if done.returncode != 0:
            raise SystemExit(f"{cmd[0]} failed on {git('branch', '--show-current')}:\n{done.stdout[-2000:]}{done.stderr[-800:]}")
    print("  verified: ruff, mypy, pytest green")


def commit(message: str) -> None:
    git("add", "-A")
    git("-c", "core.autocrlf=false", "commit", "-q", "-m", message)


def line_range(path: str, needle_start: str, needle_end: str) -> tuple[int, int]:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines, 1) if needle_start in ln)
    end = next(i for i, ln in enumerate(lines, 1) if i >= start and needle_end in ln)
    return start, end


# ----------------------------------------------------------------------------- the feature

def add_ignore_paths() -> None:
    edit("src/review_assistant/config.py", [
        ('    severity_floor: str = "low"\n',
         '    severity_floor: str = "low"\n    # Glob patterns, fnmatch syntax. A finding whose path matches any pattern is dropped.\n    ignore_paths: list[str] = field(default_factory=list)\n'),
        ('        "severity_floor",\n        "ledger_path",', '        "severity_floor",\n        "ignore_paths",\n        "ledger_path",'),
    ])
    edit("src/review_assistant/findings/filter.py", [
        ('from __future__ import annotations\n\n', 'from __future__ import annotations\n\nfrom fnmatch import fnmatch\n\n'),
        ('def in_diff(', '''def is_ignored(path: str, patterns: list[str]) -> bool:
    """Decide whether a path matches any ignore pattern."""
    return any(fnmatch(path, pattern) for pattern in patterns)


def apply_filters(findings: list[Finding], floor: str, ignore_paths: list[str]) -> list[Finding]:
    """Drop ignored paths first, then findings below the floor. Order is preserved."""
    kept = [f for f in findings if not is_ignored(f.path, ignore_paths)]
    return apply_floor(kept, floor)


def in_diff('''),
    ])
    edit("src/review_assistant/review.py", [
        ("from review_assistant.findings.filter import apply_floor, in_diff", "from review_assistant.findings.filter import apply_filters, in_diff"),
        ("    result.findings = apply_floor(raw, config.severity_floor)", "    result.findings = apply_filters(raw, config.severity_floor, config.ignore_paths)"),
    ])
    edit("tests/test_filter.py", [
        ("from review_assistant.findings.filter import apply_floor, in_diff, meets_floor", "from review_assistant.findings.filter import apply_filters, apply_floor, in_diff, meets_floor"),
    ])
    with (ROOT / "tests/test_filter.py").open("a", encoding="utf-8", newline="\n") as f:
        f.write('''

def test_ignored_path_is_dropped() -> None:
    f = [Finding(path="vendor/x.py", line=1, severity="critical", message="m")]
    assert apply_filters(f, "low", ["vendor/*"]) == []


def test_ignore_runs_before_floor_and_keeps_order() -> None:
    f = [
        Finding(path="a.py", line=1, severity="high", message="a"),
        Finding(path="b.py", line=1, severity="low", message="b"),
        Finding(path="c.py", line=1, severity="high", message="c"),
    ]
    assert [x.path for x in apply_filters(f, "medium", [])] == ["a.py", "c.py"]
''')


# ----------------------------------------------------------------------------- the five bugs

def plant_bugs() -> None:
    # B1: the hunk line mapping starts one line late (plausible logic error, in the untested path).
    edit("src/review_assistant/models.py", [
        ("            numbers.update(n for n in new_file_lines(hunk.new_start, hunk.kinds()) if n > 0)",
         "            numbers.update(n for n in new_file_lines(hunk.new_start + 1, hunk.kinds()) if n > 0)"),
    ])
    # B2: the seen set is rebuilt per call, so a redelivery posts everything again (plausible logic error).
    edit("src/review_assistant/web/worker.py", [
        ("    pr = job.pull_request\n    posted = 0\n    for finding in findings:\n        key = f\"{job.delivery}:{finding.path}:{finding.line}\"\n        if key in worker.seen:\n            continue\n        worker.seen.add(key)",
         "    pr = job.pull_request\n    posted = 0\n    seen: set[str] = set()\n    for finding in findings:\n        key = f\"{job.delivery}:{finding.path}:{finding.line}\"\n        if key in seen:\n            continue\n        seen.add(key)"),
    ])
    # B3: an invented keyword the policy accepts and ignores, so nothing ever retries (hallucinated API).
    edit("src/review_assistant/providers/base.py", [
        ("        return AnthropicProvider(model=config.model, policy=RetryPolicy(retries=3))",
         "        return AnthropicProvider(model=config.model, policy=RetryPolicy(max_retries=3))"),
        ("        return OpenAIProvider(model=config.model, policy=RetryPolicy(retries=3))",
         "        return OpenAIProvider(model=config.model, policy=RetryPolicy(max_retries=3))"),
    ])
    # B4: the budget uses a remembered model limit instead of the one passed in (stale knowledge).
    edit("src/review_assistant/context/packer.py", [
        ("    budget = model_limit - reserved_for_reply", "    budget = 8192 - reserved_for_reply"),
    ])
    # B5: the test that would have caught B2 had its expectations edited to match (weakened test).
    edit("tests/test_worker.py", [
        ('    run_job(worker, job(pr, "d41"))\n    assert run_job(worker, job(pr, "d41")) == 0\n    assert len(github.comments) == 4',
         '    run_job(worker, job(pr, "d41"))\n    # A redelivery re-posts the findings; expectations updated to match the current behavior.\n    assert run_job(worker, job(pr, "d41")) == 4\n    assert len(github.comments) == 8'),
    ])


# ----------------------------------------------------------------------------- the review branches

PR_A = """# Make provider selection extensible

Provider selection was a chain of `if` statements in `providers/base.py`. This introduces a small registry so new backends can be added without touching the factory, with plugin discovery through entry points for backends shipped as separate packages. The mock backend is registered through the new base class to prove the shape; the live backends follow in a later change.

- `providers/registry.py`: `BaseProvider`, `ProviderRegistry`, plugin loading
- `providers/base.py`: `get_provider` consults the registry first
- Tests: the registry resolves the mock and refuses an unknown name
"""

PR_B = """# Better provider logging

The provider log line only carried the token estimate, which made it hard to correlate a request with the provider's own logs when a call failed. This adds the outbound headers to the structured `extra` on the request line so a failed call can be matched end to end.

- `providers/anthropic.py`: `_log_request` logs `tokens` and `headers`
"""

PR_C = """# Record when a pull request was last updated

The worker had no way to tell how stale a job was by the time it ran. This parses the pull request's `updated_at` timestamp from the webhook event, normalizes it to UTC, and carries it on the job so the worker can log the age of what it is reviewing.

- `models.py`: `Job.updated_at`
- `web/webhook.py`: parse and normalize the timestamp
- `web/worker.py`: log the age at job start
- `pyproject.toml`: the parsing and timezone libraries
"""

PR_D = """# Limit the ledger listing

`review-assistant ledger` printed every row, which on a long-lived ledger is thousands of lines. This adds `--limit N` to print only the most recent N rows, default unlimited, with a test.

- `cli.py`: the `--limit` option on `ledger`
- `ledger/db.py`: `rows` takes an optional limit
- Tests: the limit returns the newest rows
"""

PR_E = """# Give the model the author's context

Authors often explain in the pull request description why a change looks the way it does, and the model never saw that. This passes the description into the request text, under a short heading, so the review can take the author's intent into account instead of flagging things the description already explains.

- `context/request.py`: the description is included after the instructions when a pull request is present
"""

REGISTRY = '''"""A registry of provider backends, with plugin discovery through entry points."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from importlib.metadata import entry_points

from review_assistant.config import Config
from review_assistant.models import Reply, Request
from review_assistant.providers.base import Provider

PLUGIN_GROUP = "review_assistant.providers"


class BaseProvider(ABC):
    """The base class every registered backend extends."""

    name: str = "base"

    @abstractmethod
    def complete(self, request: Request) -> Reply:
        """Send the request and return the reply."""

    def describe(self) -> str:
        """Describe the backend for diagnostics."""
        return f"{self.__class__.__name__}(name={self.name!r})"


class MockBackend(BaseProvider):
    """The mock, registered through the base class."""

    name = "mock"

    def __init__(self, config: Config) -> None:
        """Wrap the mock provider."""
        from review_assistant.providers.mock import MockProvider

        self._inner = MockProvider(config.replies_dir)

    def complete(self, request: Request) -> Reply:
        """Delegate to the mock."""
        return self._inner.complete(request)


class ProviderRegistry:
    """Backends by name, with factories that take the config."""

    def __init__(self) -> None:
        """Start empty; `defaults()` registers the built-in backends."""
        self._factories: dict[str, Callable[[Config], Provider]] = {}
        self._plugins_loaded = False

    def register(self, name: str, factory: Callable[[Config], Provider]) -> None:
        """Register a factory under a name, replacing any earlier one."""
        self._factories[name] = factory

    def names(self) -> list[str]:
        """List every registered name, sorted."""
        return sorted(self._factories)

    def load_plugins(self, group: str = PLUGIN_GROUP) -> int:
        """Register every backend advertised through the entry point group. Returns how many."""
        if self._plugins_loaded:
            return 0
        count = 0
        for entry in entry_points(group=group):
            self.register(entry.name, entry.load())
            count += 1
        self._plugins_loaded = True
        return count

    def create(self, name: str, config: Config) -> Provider:
        """Build the named backend, loading plugins first."""
        self.load_plugins()
        try:
            factory = self._factories[name]
        except KeyError as error:
            raise ValueError(f"unknown provider {name!r}; registered: {', '.join(self.names())}") from error
        return factory(config)

    @classmethod
    def defaults(cls) -> ProviderRegistry:
        """Build a registry with the built-in backends registered."""
        registry = cls()
        registry.register("mock", MockBackend)
        return registry


REGISTRY = ProviderRegistry.defaults()
'''


def branch_a() -> tuple[str, int, int]:
    write("src/review_assistant/providers/registry.py", REGISTRY)
    edit("src/review_assistant/providers/base.py", [
        ('    if config.provider == "mock":\n        from review_assistant.providers.mock import MockProvider\n\n        return MockProvider(config.replies_dir)\n',
         '    from review_assistant.providers.registry import REGISTRY\n\n    if config.provider in REGISTRY.names():\n        return REGISTRY.create(config.provider, config)\n'),
    ])
    write("tests/test_registry.py", '''from pathlib import Path

import pytest

from review_assistant.config import Config
from review_assistant.providers.registry import ProviderRegistry
from tests.helpers import REPLIES


def test_the_registry_resolves_the_mock(tmp_path: Path) -> None:
    registry = ProviderRegistry.defaults()
    provider = registry.create("mock", Config(replies_dir=str(REPLIES)))
    assert provider.name == "mock"


def test_an_unknown_name_is_refused_with_the_registered_names() -> None:
    with pytest.raises(ValueError) as error:
        ProviderRegistry.defaults().create("nope", Config())
    assert "mock" in str(error.value)
''')
    write("PULL_REQUEST.md", PR_A)
    lines = (ROOT / "src/review_assistant/providers/registry.py").read_text(encoding="utf-8").splitlines()
    return "src/review_assistant/providers/registry.py", 1, len(lines)


def branch_b() -> tuple[str, int, int]:
    edit("src/review_assistant/providers/anthropic.py", [
        ('    def _log_request(self, request: Request) -> None:\n        log.info("request     %s", fields(path=request.path, tokens=estimate_tokens(request.text)))\n',
         '    def _log_request(self, request: Request) -> None:\n        """Log the outbound request with enough to match it against the provider\'s own logs."""\n        log.info(\n            "request     %s",\n            fields(path=request.path, tokens=estimate_tokens(request.text), headers=request.headers),\n        )\n'),
    ])
    write("PULL_REQUEST.md", PR_B)
    return ("src/review_assistant/providers/anthropic.py", *line_range("src/review_assistant/providers/anthropic.py", "def _log_request", "headers=request.headers"))


def branch_c() -> tuple[str, int, int]:
    edit("pyproject.toml", [
        ('    "pyyaml>=6",\n]', '    "pyyaml>=6",\n    "python-dateutil>=2.9",\n    "pytz>=2024.1",\n]'),
        ('    "types-PyYAML",\n', '    "types-PyYAML",\n    "types-python-dateutil",\n    "types-pytz",\n'),
    ])
    edit("src/review_assistant/models.py", [
        ('from dataclasses import dataclass, field\n', 'from dataclasses import dataclass, field\nfrom datetime import datetime\n'),
        ('    pull_request: PullRequest\n    delivery: str\n    installation: int = 0\n',
         '    pull_request: PullRequest\n    delivery: str\n    installation: int = 0\n    updated_at: datetime | None = None\n'),
    ])
    edit("src/review_assistant/web/webhook.py", [
        ('from typing import Any\n\n', 'from typing import Any\n\nimport pytz\nfrom dateutil import parser as dateparser\n'),
        ('    installation = int((event.get("installation") or {}).get("id") or 0)\n    return Job(pull_request=pr, delivery=delivery, installation=installation)',
         '    installation = int((event.get("installation") or {}).get("id") or 0)\n    updated_at = None\n    if pull.get("updated_at"):\n        updated_at = dateparser.isoparse(str(pull["updated_at"])).astimezone(pytz.UTC)\n    return Job(pull_request=pr, delivery=delivery, installation=installation, updated_at=updated_at)'),
    ])
    edit("src/review_assistant/web/worker.py", [
        ('from dataclasses import dataclass, field\n', 'from dataclasses import dataclass, field\nfrom datetime import UTC, datetime\n'),
        ('    log.info("job start   %s", fields(pr=pr.number, delivery=job.delivery, installation=job.installation))\n',
         '    age = int((datetime.now(UTC) - job.updated_at).total_seconds()) if job.updated_at else None\n    log.info(\n        "job start   %s",\n        fields(pr=pr.number, delivery=job.delivery, installation=job.installation, age_seconds=age),\n    )\n'),
    ])
    write("PULL_REQUEST.md", PR_C)
    return ("pyproject.toml", *line_range("pyproject.toml", '"python-dateutil>=2.9"', '"pytz>=2024.1"'))


def branch_d() -> None:
    edit("src/review_assistant/ledger/db.py", [
        ('def rows(engine: Engine) -> list[Review]:\n    """Every ledger row, oldest first."""\n    with Session(engine) as session:\n        found = list(session.scalars(select(Review).order_by(Review.id)).all())',
         'def rows(engine: Engine, limit: int | None = None) -> list[Review]:\n    """Every ledger row, oldest first; with a limit, only the newest `limit` rows."""\n    with Session(engine) as session:\n        statement = select(Review).order_by(Review.id)\n        if limit is not None:\n            newest = select(Review.id).order_by(Review.id.desc()).limit(limit).subquery()\n            statement = statement.where(Review.id.in_(select(newest.c.id)))\n        found = list(session.scalars(statement).all())'),
    ])
    edit("src/review_assistant/cli.py", [
        ('def ledger(config_file: Path = typer.Option(Path(".review-assistant.yml"), "--config")) -> None:\n    """Print every ledger row: when, provider, model, pull request, tokens and cents."""\n    config = load_config(config_file)\n    for row in rows(connect(config.ledger_path)):',
         'def ledger(\n    config_file: Path = typer.Option(Path(".review-assistant.yml"), "--config"),\n    limit: int | None = typer.Option(None, "--limit", help="Print only the newest N rows."),\n) -> None:\n    """Print the ledger rows: when, provider, model, pull request, tokens and cents."""\n    config = load_config(config_file)\n    for row in rows(connect(config.ledger_path), limit):'),
    ])
    with (ROOT / "tests/test_ledger.py").open("a", encoding="utf-8", newline="\n") as f:
        f.write('''

def test_a_limit_returns_the_newest_rows_in_order(tmp_path: Path) -> None:
    engine = connect(tmp_path / "ledger.sqlite")
    for cents in (1, 2, 3):
        record_review(engine, provider="mock", model="m", input_tokens=1, output_tokens=1, cents=cents)
    assert [r.cents for r in rows(engine, limit=2)] == [2, 3]
    assert [r.cents for r in rows(engine)] == [1, 2, 3]
''')
    write("PULL_REQUEST.md", PR_D)


def branch_e() -> tuple[str, int, int]:
    edit("src/review_assistant/context/request.py", [
        ('    text = INSTRUCTIONS + "\\n\\n" + render_file(file)\n    return Request(text=text, model=model, path=file.path)',
         '    text = INSTRUCTIONS\n    if pr is not None and pr.description.strip():\n        text += "\\n\\nContext from the author:\\n" + pr.description.strip()\n    text += "\\n\\n" + render_file(file)\n    return Request(text=text, model=model, path=file.path)'),
        ('    request. Template version one is the instructions, a blank line, and the rendered file. The pull\n    request is accepted so that later template versions can use it; version one does not.',
         '    request. Template version one is the instructions, the author\'s context from the pull request\n    description when there is one, and the rendered file.'),
    ])
    write("PULL_REQUEST.md", PR_E)
    return ("src/review_assistant/context/request.py", *line_range("src/review_assistant/context/request.py", "if pr is not None", 'text += "\\n\\n" + render_file(file)'))


CHECK_06 = '''"""Lab 6, spot the bug: the right defects in the right places on the five review branches, and nothing else."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, check, finish, skip  # noqa: E402

LAB = "labs/check-06"
BRANCHES = ["review-a", "review-b", "review-c", "review-d", "review-e"]
# branch -> (sha256 of the planted file's path, first line, last line) or None for the clean branch.
PLANTED: dict[str, tuple[str, int, int] | None] = __PLANTED__
SEVERITIES = {"low", "medium", "high", "critical"}
DEFECT = re.compile(r"^- DEFECT:\\s*(?P<path>[^\\s#]+)(?:#\\S+)?\\s+line\\s+(?P<line>\\d+)\\b.*?SEVERITY:\\s*(?P<severity>\\w+)", re.IGNORECASE)


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
'''


def main() -> None:
    start = git("branch", "--show-current")
    base = git("rev-parse", "HEAD")
    if git("status", "--porcelain"):
        raise SystemExit("the working tree must be clean")
    planted: dict[str, tuple[str, int, int] | None] = {}

    # The feature, on a throwaway branch that is never pushed.
    git("checkout", "-q", "-B", "tmp/ignore-paths", base)
    add_ignore_paths()
    verify()
    commit("Add ignore paths to the review assistant config\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>")
    print("ignore-paths feature built")

    # The orphan bugs branch: the feature tree plus five bugs, one squashed commit.
    git("checkout", "-q", "--orphan", "module-4-bugs")
    plant_bugs()
    verify()
    git("add", "-A")
    git("-c", "core.autocrlf=false", "commit", "-q", "-m", "The review assistant, as the debugging lab finds it\n\nFive bugs, described by symptom in the course. No history, on purpose.")
    print("module-4-bugs built:", git("rev-parse", "--short", "HEAD"))

    # The review branches, each one commit off the base.
    builders = {"review-a": branch_a, "review-b": branch_b, "review-c": branch_c, "review-d": branch_d, "review-e": branch_e}
    titles = {"review-a": "Make provider selection extensible", "review-b": "Better provider logging", "review-c": "Record when a pull request was last updated", "review-d": "Limit the ledger listing", "review-e": "Give the model the author's context"}
    for name, builder in builders.items():
        git("checkout", "-q", "-B", name, base)
        result = builder()
        if name == "review-c":
            sh(PY, "-m", "pip", "install", "-q", "python-dateutil", "pytz", "types-python-dateutil", "types-pytz")
        verify()
        commit(f"{titles[name]}\n\nSee PULL_REQUEST.md for the description.")
        if result is None:
            planted[name] = None
        else:
            path, lo, hi = result
            planted[name] = (hashlib.sha256(path.encode()).hexdigest(), lo, hi)
        print(f"{name} built: {git('rev-parse', '--short', 'HEAD')} planted={planted[name]}")

    git("checkout", "-q", start)
    git("branch", "-q", "-D", "tmp/ignore-paths")
    write("labs/checks/check_06.py", CHECK_06.replace("__PLANTED__", repr(planted)))
    print("labs/checks/check_06.py written on", start)


if __name__ == "__main__":
    main()
