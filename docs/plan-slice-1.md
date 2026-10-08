# Plan: slice one

Each step names the files it touches and the check that proves it, following the course's own Lesson 3.2. A step without a check is not a step.

| # | Step | Files | Check |
|---|---|---|---|
| 1 | Package skeleton, tooling, CI | `pyproject.toml`, `src/review_assistant/__init__.py`, `tests/test_smoke.py`, `.github/workflows/ci.yml` | CI green on an empty package |
| 2 | Data types | `models.py` (`FileDiff`, `Hunk`, `Finding`, `Request`, `Reply`, `Pack`) | mypy clean; a round-trip test per type |
| 3 | Line mapping | `diff/lines.py` | unit tests including first and last line of a hunk, all-removed hunk |
| 4 | Diff parser | `diff/parser.py` | no tests, by design; a smoke run over every fixture patch does not raise |
| 5 | Severity filter and cost arithmetic | `findings/filter.py`, `ledger/cost.py` | unit tests; hypothesis property: filter preserves order and is idempotent |
| 6 | Provider interface and mock | `providers/base.py`, `providers/mock.py`, `fixtures/replies/` | a recorded reply replays byte for byte; a missing key raises a clear error |
| 7 | Live providers | `providers/anthropic.py`, `providers/openai.py` | an integration test skipped unless the key is present; fixtures recorded once and committed |
| 8 | Context packer | `context/packer.py` | unit tests for the budget boundary; the drop order is end first |
| 9 | Ledger | `ledger/db.py`, `alembic/` | `alembic upgrade head` on an empty SQLite file creates the table; a review inserts one row |
| 10 | Config | `config.py` | missing file gives defaults; a bad floor value is rejected with the allowed list |
| 11 | Command | `cli.py` | acceptance examples 1 to 5 from the spec as tests |
| 12 | Docstrings and README | all modules, `README.md` | every public function has a docstring that matches a test |

Done means: every check in the table passes, `ruff`, `mypy` and `pytest` are green in CI, and the seven acceptance examples in the spec are each covered by a test.
