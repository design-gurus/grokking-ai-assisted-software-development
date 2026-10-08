import hashlib
import hmac
import json
from pathlib import Path

from fastapi.testclient import TestClient

from review_assistant.config import Config
from review_assistant.models import PullRequest
from review_assistant.providers.mock import MockProvider
from review_assistant.web.webhook import create_app, job_from_event, verify_signature
from review_assistant.web.worker import Worker
from tests.fakes import FakeGitHub
from tests.helpers import REPLIES, patch_text

SECRET = "course-secret"


def signed(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def event(action: str = "opened") -> dict[str, object]:
    return {
        "action": action,
        "repository": {"full_name": "design-gurus/example"},
        "installation": {"id": 7},
        "pull_request": {
            "number": 118,
            "title": "Tidy the filter",
            "body": "",
            "user": {"login": "someone"},
            "head": {"sha": "abc1234"},
            "base": {"sha": "def5678"},
        },
    }


def make_app(tmp_path: Path) -> tuple[TestClient, FakeGitHub]:
    pr = PullRequest(repo="design-gurus/example", number=118, head_sha="abc1234", base_sha="def5678")
    github = FakeGitHub(pr=pr, diff_text=patch_text("three-files.patch"))
    config = Config(ledger_path=str(tmp_path / "ledger.sqlite"), replies_dir=str(REPLIES))
    worker = Worker(client=github, provider=MockProvider(REPLIES), config=config, engine=None)
    return TestClient(create_app(worker, SECRET)), github


def test_the_signature_is_verified_in_constant_time() -> None:
    body = b'{"x": 1}'
    assert verify_signature(SECRET, body, signed(body))
    assert not verify_signature(SECRET, body, "sha256=" + "0" * 64)
    assert not verify_signature(SECRET, body, None)


def test_a_bad_signature_is_refused_before_anything_is_parsed(tmp_path: Path) -> None:
    client, github = make_app(tmp_path)
    headers = {"X-Hub-Signature-256": "sha256=bad", "X-GitHub-Event": "pull_request"}
    response = client.post("/webhook", content=b"not json", headers=headers)
    assert response.status_code == 401
    assert github.comments == []


def test_a_pull_request_event_runs_a_job_and_posts_comments(tmp_path: Path) -> None:
    client, github = make_app(tmp_path)
    body = json.dumps(event()).encode()
    response = client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": signed(body),
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "d41",
        },
    )
    assert response.status_code == 200 and response.json()["queued"] is True
    assert len(github.comments) == 4


def test_other_actions_are_ignored() -> None:
    assert job_from_event(event("closed"), "d1") is None
    job = job_from_event(event("synchronize"), "d2")
    assert job is not None and job.pull_request.number == 118 and job.installation == 7
