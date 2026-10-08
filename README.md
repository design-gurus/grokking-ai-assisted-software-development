# Pull request review assistant

A small service that takes a pull request, reads the diff, asks a model for findings, and posts them back as review comments. It is the shared codebase for the Design Gurus course **Grokking AI-Assisted Software Development**: every lab in the course builds on this repository, in your own fork.

## Status

Slice one, in progress: the command line mode. A patch file goes in, findings come out, through the diff parser, the context packer, the provider layer and the cost ledger. The webhook receiver, queue and worker are slice two. See `docs/spec-slice-1.md` for the specification this slice is built against and `docs/plan-slice-1.md` for the plan with a check per step.

## What it is, and what it is not

It is a plain model-backed service: one model request per changed file, no agent loop, no tool use, no retrieval index. It will stay that way. The course it serves teaches engineers who use AI tools on code; it does not teach how to build agents, and the moment this repository grows an agent it starts teaching the wrong course.

It is a teaching service. You can run it against your own patches in command line mode after the course. It is not a replacement for a hosted code reviewer.

## Layout

```
src/review_assistant/   the service
tests/                  the test suite (runs on the mock provider; no API key needed)
fixtures/               patches and recorded model replies the mock provider replays
labs/                   setup and fixtures for each lab; the tasks themselves live in the course
docs/                   specifications and plans, one per slice
.github/workflows/      CI: lint, type check, tests, and one check job per lab
```

## Running it

```
python -m venv .venv
.venv/Scripts/activate            # Windows
source .venv/bin/activate         # macOS, Linux
pip install -e ".[dev]"
pytest
```

The provider defaults to `mock`, which replays recorded replies from `fixtures/`. Set `REVIEW_PROVIDER=anthropic` or `REVIEW_PROVIDER=openai` with the matching API key to call a live model.

## Instruction files

`AGENTS.md` is the instruction file for AI coding tools. `CLAUDE.md` and `GEMINI.md` point at it. The course asks you to read these files in Lesson 1.5 and to improve them in Lesson 7.4, so they are deliberately not perfect.

## License

MIT. See `LICENSE`.
