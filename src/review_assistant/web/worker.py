"""The worker: take a job, review the pull request, post the findings as comments."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.engine import Engine

from review_assistant.config import Config
from review_assistant.diff.parser import parse
from review_assistant.log import fields, get_logger
from review_assistant.models import FileDiff, Finding, Job
from review_assistant.providers.base import Provider
from review_assistant.review import review_files
from review_assistant.web.cache import FindingsCache
from review_assistant.web.github import GitHubApi

log = get_logger("worker")


@dataclass
class Worker:
    """Everything a job needs, held once per process."""

    client: GitHubApi
    provider: Provider
    config: Config
    engine: Engine | None
    cache: FindingsCache = field(default_factory=FindingsCache)
    seen: set[str] = field(default_factory=set)
    posted: list[tuple[int, str, int, str]] = field(default_factory=list)


def run_job(worker: Worker, job: Job) -> int:
    """Review the job's pull request and post one comment per finding. Returns how many were posted.

    A pull request that was reviewed before is served from the findings cache, so a webhook
    redelivery costs no model call.
    """
    pr = job.pull_request
    age = int((datetime.now(UTC) - job.updated_at).total_seconds()) if job.updated_at else None
    log.info(
        "job start   %s",
        fields(pr=pr.number, delivery=job.delivery, installation=job.installation, age_seconds=age),
    )
    cached = worker.cache.findings_for(pr.number)
    if cached is not None:
        findings = cached
    else:
        diff_text = worker.client.diff(pr.repo, pr.number)
        files = parse(diff_text)
        log.info("fetch diff  %s", fields(pr=pr.number, files=len(files)))
        attach_neighbors(worker, files, pr.repo, pr.head_sha)
        result = review_files(files, worker.config, worker.provider, worker.engine, pr, job.delivery)
        findings = result.findings
        worker.cache.store(pr.number, findings)
    comments = post_findings(worker, job, findings)
    log.info("job done    %s", fields(pr=pr.number, posted=comments))
    return comments


def attach_neighbors(worker: Worker, files: list[FileDiff], repo: str, ref: str) -> None:
    """Fetch the lines around every hunk from the repository at the head commit.

    One fetch per hunk: each hunk asks for the file it sits in and takes the lines around itself.
    """
    for file in files:
        if file.is_binary or file.is_deleted:
            continue
        parts: list[str] = []
        for hunk in file.hunks:
            contents = worker.client.get_file(repo, file.path, ref)
            parts.append(contents.lines_around(hunk))
        file.neighbors = "\n".join(parts)


def post_findings(worker: Worker, job: Job, findings: list[Finding]) -> int:
    """Post each finding once per delivery, in order, and return how many were posted.

    The seen set is keyed on the delivery id and the finding's location, so a redelivered event
    posts nothing twice while a new push, which arrives under a new delivery id, posts afresh.
    """
    pr = job.pull_request
    posted = 0
    for finding in findings:
        key = f"{job.delivery}:{finding.path}:{finding.line}"
        if key in worker.seen:
            continue
        worker.seen.add(key)
        body = f"**{finding.severity}**: {finding.message}"
        worker.client.post_review_comment(pr.repo, pr.number, pr.head_sha, finding.path, finding.line, body)
        worker.posted.append((pr.number, finding.path, finding.line, body))
        log.info("post        %s", fields(pr=pr.number, path=finding.path, line=finding.line))
        posted += 1
    return posted
