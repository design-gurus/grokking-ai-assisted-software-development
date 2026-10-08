# Fixtures

- `patches/`: unified diffs the command reviews and the tests parse.
- `replies/`: recorded model replies, keyed by the SHA-256 of the request text. The mock provider replays them. They are recorded once from a live model and committed; they are never edited by hand.
