"""A small in-process job queue between the webhook and the worker."""

from __future__ import annotations

from collections import deque

from review_assistant.models import Job


class JobQueue:
    """First in, first out. One process; the course does not need more."""

    def __init__(self) -> None:
        """Start empty."""
        self._jobs: deque[Job] = deque()

    def enqueue(self, job: Job) -> None:
        """Add a job at the back."""
        self._jobs.append(job)

    def dequeue(self) -> Job | None:
        """Take the job at the front, or None when the queue is empty."""
        return self._jobs.popleft() if self._jobs else None

    def __len__(self) -> int:
        """How many jobs are waiting."""
        return len(self._jobs)
