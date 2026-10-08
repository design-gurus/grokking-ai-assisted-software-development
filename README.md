# Pull request review assistant

A small service that takes a pull request, reads the diff, asks a model for findings, and posts them back as review comments. It is the shared codebase for the Design Gurus course **Grokking AI-Assisted Software Development**: every lab in the course builds on this repository, in your own fork.

## What it is, and what it is not

It is a plain model-backed service: one model request per changed file, no agent loop, no tool use, no retrieval index. It will stay that way. The course it serves teaches engineers who use AI tools on code; it does not teach how to build agents, and the moment this repository grows an agent it starts teaching the wrong course.

It is a teaching service. You can run it against your own patches in command line mode after the course. It is not a replacement for a hosted code reviewer.

## Layout

```
src/review_assistant/
  cli.py                the command: review a patch file, print findings and the cost
  config.py             .review-assistant.yml at the repository root, with environment overrides
  models.py             FileDiff, Hunk, Finding, Request, Reply, PullRequest, Job
  review.py             the review itself: pack, one request per file, filter, bill
  diff/parser.py        the hand-written unified diff parser (no tests, by design)
  diff/lines.py         hunk lines to new-file line numbers
  context/packer.py     which files fit the token budget
  context/request.py    the text the model reads
  findings/filter.py    the severity floor, and lines that must be in the diff
  findings/parse.py     the model's JSON array to findings
  ledger/cost.py        cents, rounded half up
  ledger/db.py          the SQLite ledger, migrated with Alembic
  providers/            the interface, the mock, Anthropic, OpenAI, and the retry policy
  web/webhook.py        the FastAPI receiver: signature, event, queue
  web/queue.py          the in-process job queue
  web/worker.py         take a job, review the pull request, post comments
  web/github.py         the GitHub client
  web/cache.py          findings remembered per pull request
tests/                  the suite; runs on the mock provider, no API key needed
fixtures/patches/       unified diffs the command reviews
fixtures/replies/       recorded model replies the mock replays, keyed by the request text's SHA-256
alembic/                the ledger's migrations
labs/                   the lab check jobs (labs/checks/) and the testing module's drill
docs/                   the specification and the plan for each slice
.github/workflows/      ci.yml: lint, strict types, the suite, a secret scan; labs.yml: one job per lab
```

## Running it

```
python -m venv .venv
.venv/Scripts/activate            # Windows
source .venv/bin/activate         # macOS, Linux
pip install -e ".[dev]"
pytest
review-assistant review fixtures/patches/three-files.patch
review-assistant review fixtures/patches/three-files.patch --format json
review-assistant ledger
```

The provider defaults to `mock`, which replays recorded replies from `fixtures/replies/`. Set `REVIEW_PROVIDER=anthropic` or `REVIEW_PROVIDER=openai` with the matching API key in the environment to call a live model. Keys are never read from files in this repository.

The per-repository config file is `.review-assistant.yml` at the root. It holds `severity_floor` (`low`, `medium`, `high`, `critical`), `provider`, `model`, `model_limit`, `reserved_for_reply`, `ledger_path` and `request_template_version`. A missing file gives the defaults.

## The branches and tags the course uses

- `module-2` and `module-3`: tags on the base the understanding and writing labs start from.
- `module-4-bugs`: an orphan branch with the ignore-paths feature in place and five bugs planted, described by symptom in the course. No history to diff against, on purpose.
- `review-a` to `review-e`: five pull-request-shaped branches for the review lab. Four carry one planted defect each; one is clean. Each has a `PULL_REQUEST.md` with the description a reviewer would see.

The lab tasks, their acceptance checklists and the exemplar artifacts live in the course, not here. The check jobs in `labs/checks/` are what the course calls `labs/check-02` through `labs/check-07`; they run on your fork's pull requests and print one line per criterion.

## Properties of the base that the course relies on

- The diff parser in `src/review_assistant/diff/parser.py` ships without tests. The refactoring lesson gives it a characterization suite; the testing module gives it a second opinion from the `unidiff` library.
- The worker fetches a file's contents once per hunk, not once per file. The performance lesson's profile finds it.
- The findings cache in `src/review_assistant/web/cache.py` is keyed by pull request number, so a second push on an already reviewed pull request is served the previous push's findings.
- The Anthropic SDK is pinned below its current major in `pyproject.toml`. The migration lesson moves the pin.

## Recorded replies

`fixtures/replies/` holds one JSON file per request the fixtures produce, written by `scripts/make_fixtures.py`. The replies in the repository are authored findings in the shape a live reply has. Run `python scripts/make_fixtures.py --live anthropic` with a key in the environment to replace them with real recorded replies; the file names stay the same because the request text does.

## Instruction files

`AGENTS.md` is the instruction file for AI coding tools. `CLAUDE.md` and `GEMINI.md` point at it. The course asks you to read these files in Lesson 1.5 and to improve them in Lesson 7.4, so they are deliberately not perfect.

## License

MIT. See `LICENSE`.
