# Specification: slice one, the command line review

Written before any code, following the course's own first step. One page: goal, users, constraints, non-goals, then acceptance examples.

## Goal

A command reviews a unified diff from a local patch file and prints findings, each with a file, a line in the new file, a severity and a message, using a model behind a provider interface. The same code path later serves the webhook worker in slice two.

## Users

- A course student who clones the repository and runs the command within five minutes of cloning, with no API key.
- The course author, who records real model replies once and commits them as fixtures.
- Slice two, which calls the same review function from a worker instead of a command.

## Constraints

- Python 3.12. No framework in slice one beyond what the command needs; FastAPI arrives with the webhook in slice two.
- The provider interface has three backends: `anthropic`, `openai` and `mock`. The mock replays a recorded reply keyed by the SHA-256 of the request text. Tests and CI use only the mock.
- One model request per changed file. No agent loop, no tool use, no retrieval.
- The diff parser is hand written and ships without tests. This is deliberate: it is the legacy module the course refactors in Lesson 3.7. Every other module ships with tests.
- The context packer stays within a token budget computed from the model limit passed in, never from a constant.
- Findings carry a line number in the new file. The mapping from hunk offsets to new-file lines is the parser's job and the course's first graded exercise, so it must be a single function with a clear signature.
- The cost ledger is a SQLite table written through SQLAlchemy and migrated with Alembic from the first version, so that the slice two schema change has a real migration history to extend.
- The per-repository config file is `.review-assistant.yml` at the repository root: `severity_floor` (`low`, `medium`, `high`, `critical`), the provider and model, the token budget and the ledger path. There is no `ignore_paths` setting on purpose: adding it is the Module 3 lab feature.
- Anthropic SDK pinned below its current major. The upgrade is the Module 3 migration lesson and is recorded when it is done.
- Every module has a docstring that says what it does today. Comments say why, never what.

## Non-goals for slice one

- Receiving webhooks, queueing, GitHub App authentication, posting comments, pagination. All slice two.
- Caching findings. Slice two, where it is keyed by pull request number.
- Any deduplication, sorting or grouping of findings. The filter returns what the model returned, minus what is below the floor, in order.

## Acceptance examples

1. `review-assistant review fixtures/patches/001-rename-helper.patch` prints a table of findings and a one-line cost summary, using the mock provider, with no network access and no environment variables set.
2. The same command with `--format json` prints a JSON array where every finding has `path`, `line`, `severity`, `message`, and `line` is a line number in the new file.
3. With `severity_floor: high` in the config, findings below high are absent from the output and the ledger still records the full cost of the request.
4. A patch touching three files produces exactly three provider requests, visible in the mock's call log.
5. A request whose packed context would exceed `model_limit - reserved_for_reply` tokens drops files from the end of the pack until it fits, and says so on stderr.
6. `pytest` passes with no API key present. `ruff check` and `mypy` pass.
7. The ledger row for a review carries the provider name, input tokens, output tokens and cost in cents, rounded half up.

## Components and their public functions

| Module | Function | Signature |
|---|---|---|
| `diff/parser.py` | parse a unified diff | `parse(text: str) -> list[FileDiff]` |
| `diff/lines.py` | map hunk line kinds to new-file lines | `new_file_lines(new_start: int, kinds: list[str]) -> list[int]` |
| `context/packer.py` | choose what goes in the request | `pack(files: list[FileDiff], model_limit: int, reserved_for_reply: int) -> Pack`; keeps the caller's order; the first file that does not fit ends the pack and every file after it is dropped; `FileDiff` carries `path`, `patch` and `neighbors` (the unchanged lines around each hunk); the canonical source is the module shown in course lesson 2.1 |
| `providers/base.py` | the interface | `class Provider: def complete(self, request: Request) -> Reply` |
| `providers/mock.py` | replay recorded replies | keyed by `sha256(request.text)` |
| `findings/filter.py` | apply the severity floor | `meets_floor(severity: str, floor: str) -> bool` and `apply_floor(findings: list[Finding], floor: str) -> list[Finding]` |
| `ledger/cost.py` | cost arithmetic | `review_cost_cents(input_tokens, output_tokens, input_cents_per_million, output_cents_per_million) -> int` |
| `cli.py` | the command | `review-assistant review <patch> [--format table|json] [--provider mock|anthropic|openai]` |

The functions in `diff/lines.py`, `findings/filter.py` and `ledger/cost.py` are the components the course's graded exercises are mutated from, so their signatures are fixed by the exercise dry runs and do not change without a note in `docs/`.
