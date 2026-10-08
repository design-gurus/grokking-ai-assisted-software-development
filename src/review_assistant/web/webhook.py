"""The webhook receiver: verify the signature, read the event, queue a job, run the worker."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from review_assistant.models import Job, PullRequest
from review_assistant.web.queue import JobQueue
from review_assistant.web.worker import Worker, run_job

ACTIONS = ("opened", "synchronize", "reopened")


def verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    """Check that the `X-Hub-Signature-256` header matches the body under the shared secret.

    The comparison is constant-time. A missing header never verifies.
    """
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[len("sha256=") :])


def job_from_event(event: dict[str, Any], delivery: str) -> Job | None:
    """Build a job for a pull request event the service reviews, or None for anything else."""
    if event.get("action") not in ACTIONS or "pull_request" not in event:
        return None
    pull = event["pull_request"]
    repo = str(event["repository"]["full_name"])
    pr = PullRequest(
        repo=repo,
        number=int(pull["number"]),
        head_sha=str(pull["head"]["sha"]),
        base_sha=str(pull["base"]["sha"]),
        title=str(pull.get("title") or ""),
        description=str(pull.get("body") or ""),
        author=str((pull.get("user") or {}).get("login") or ""),
    )
    installation = int((event.get("installation") or {}).get("id") or 0)
    return Job(pull_request=pr, delivery=delivery, installation=installation)


def create_app(worker: Worker, secret: str, queue: JobQueue | None = None) -> FastAPI:
    """Build the FastAPI application. The worker runs each job in the background after the response."""
    app = FastAPI(title="review assistant")
    jobs = queue or JobQueue()

    def drain() -> None:
        while (job := jobs.dequeue()) is not None:
            run_job(worker, job)

    @app.post("/webhook")
    async def webhook(
        request: Request,
        background: BackgroundTasks,
        x_hub_signature_256: str | None = Header(default=None),
        x_github_delivery: str = Header(default=""),
        x_github_event: str = Header(default=""),
    ) -> dict[str, object]:
        body = await request.body()
        if not verify_signature(secret, body, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="bad signature")
        if x_github_event != "pull_request":
            return {"queued": False, "reason": f"ignored event {x_github_event}"}
        job = job_from_event(json.loads(body), x_github_delivery)
        if job is None:
            return {"queued": False, "reason": "ignored action"}
        jobs.enqueue(job)
        background.add_task(drain)
        return {"queued": True, "pull_request": job.pull_request.number, "delivery": job.delivery}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app
