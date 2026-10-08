# Fixtures

- `patches/`: unified diffs the command reviews and the tests parse.
- `replies/`: the mock provider's replies, keyed by the SHA-256 of the request text, one JSON file per request. Written by `scripts/make_fixtures.py`: today they are authored findings in the shape a live reply has, so the course runs with no API key; `--live` replaces them with real recorded replies under the same names. They are never edited by hand.
