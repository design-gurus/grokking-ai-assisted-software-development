# Instructions for AI coding tools

This repository is a pull request review assistant in Python 3.12. Read `README.md` for what it is and what it is not, and `docs/spec-slice-1.md` for the specification the current slice is built against.

## Commands

- Install: `pip install -e ".[dev]"`
- Lint: `ruff check .`
- Type check: `mypy`
- Tests: `pytest` (uses the mock provider; no API key needed)

## Conventions

- Source lives in `src/review_assistant/`, tests in `tests/`, one test module per source module.
- Every public function has a docstring that says what it does today. Comments say why, never what.
- The provider defaults to `mock`. Never make a test depend on a live model.
- The diff parser in `diff/parser.py` has no tests by design. Do not add tests to it unless asked.
- Do not add an agent loop, tool use or retrieval. One model request per changed file.
- Do not upgrade the Anthropic SDK across a major version. The pin is deliberate.

## What never to do

- Never commit an API key, a `.env` file or a real pull request's contents as a fixture.
- Never edit files under `fixtures/replies/`; they are recorded, not written.
