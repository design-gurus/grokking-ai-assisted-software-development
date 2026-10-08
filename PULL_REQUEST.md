# Better provider logging

The provider log line only carried the token estimate, which made it hard to correlate a request with the provider's own logs when a call failed. This adds the outbound headers to the structured `extra` on the request line so a failed call can be matched end to end.

- `providers/anthropic.py`: `_log_request` logs `tokens` and `headers`
