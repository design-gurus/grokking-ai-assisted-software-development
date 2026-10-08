# Limit the ledger listing

`review-assistant ledger` printed every row, which on a long-lived ledger is thousands of lines. This adds `--limit N` to print only the most recent N rows, default unlimited, with a test.

- `cli.py`: the `--limit` option on `ledger`
- `ledger/db.py`: `rows` takes an optional limit
- Tests: the limit returns the newest rows
