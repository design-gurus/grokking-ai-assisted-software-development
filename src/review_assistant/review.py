"""The review itself: parse, pack, one request per file, findings, the ledger row.

The command line mode and the worker both call `review_files`. The command gets its files from a
patch on disk; the worker gets them from the pull request and adds the lines around each hunk.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.engine import Engine

from review_assistant.config import Config
from review_assistant.context.packer import Pack, pack
from review_assistant.context.request import build_request
from review_assistant.findings.filter import apply_filters, in_diff
from review_assistant.findings.parse import parse_reply
from review_assistant.ledger.cost import cost_for
from review_assistant.ledger.db import record_review
from review_assistant.log import fields, get_logger
from review_assistant.models import FileDiff, Finding, PullRequest, Request
from review_assistant.providers.base import Provider

log = get_logger("packer")


@dataclass
class ReviewResult:
    """What a review produced: the findings that passed the filters, the cost, and what was dropped."""

    findings: list[Finding] = field(default_factory=list)
    cents: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    dropped: list[str] = field(default_factory=list)
    requests: list[Request] = field(default_factory=list)


def review_files(
    files: list[FileDiff],
    config: Config,
    provider: Provider,
    engine: Engine | None,
    pr: PullRequest | None = None,
    delivery: str | None = None,
) -> ReviewResult:
    """Review the changed files: pack them, ask the provider once per file, filter, and bill.

    Binary and deleted files are skipped before packing. The ledger records the whole review's
    tokens as one row, before the floor is applied, because the model was paid for every finding.
    """
    reviewable = [f for f in files if not f.is_binary and not f.is_deleted and f.hunks]
    packed: Pack = pack(reviewable, config.model_limit, config.reserved_for_reply)
    log.info(
        "pack        %s",
        fields(pr=pr.number if pr else "-", tokens=packed.tokens, dropped=len(packed.dropped)),
    )
    result = ReviewResult(dropped=list(packed.dropped))
    raw: list[Finding] = []
    for file in packed.files:
        request = build_request(file, config.model, config.request_template_version, pr)
        result.requests.append(request)
        reply = provider.complete(request)
        result.input_tokens += reply.input_tokens
        result.output_tokens += reply.output_tokens
        raw.extend(in_diff(parse_reply(reply.content, file.path), file))
    result.cents = cost_for(config.model, result.input_tokens, result.output_tokens)
    if engine is not None and packed.files:
        record_review(
            engine,
            provider=provider.name,
            model=config.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cents=result.cents,
            pull_request=pr.number if pr else None,
            delivery=delivery,
        )
    result.findings = apply_filters(raw, config.severity_floor, config.ignore_paths)
    return result
