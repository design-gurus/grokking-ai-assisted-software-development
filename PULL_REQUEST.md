# Record when a pull request was last updated

The worker had no way to tell how stale a job was by the time it ran. This parses the pull request's `updated_at` timestamp from the webhook event, normalizes it to UTC, and carries it on the job so the worker can log the age of what it is reviewing.

- `models.py`: `Job.updated_at`
- `web/webhook.py`: parse and normalize the timestamp
- `web/worker.py`: log the age at job start
- `pyproject.toml`: the parsing and timezone libraries
