from pathlib import Path

from review_assistant.config import Config
from review_assistant.diff.parser import parse
from review_assistant.models import Job, PullRequest
from review_assistant.providers.mock import MockProvider
from review_assistant.web.worker import Worker, run_job
from tests.fakes import FakeGitHub
from tests.helpers import REPLIES, patch_text


def make_worker(tmp_path: Path, patch: str = "three-files.patch") -> tuple[Worker, FakeGitHub, PullRequest]:
    pr = PullRequest(repo="design-gurus/example", number=118, head_sha="abc1234", base_sha="def5678")
    github = FakeGitHub(pr=pr, diff_text=patch_text(patch))
    config = Config(ledger_path=str(tmp_path / "ledger.sqlite"), replies_dir=str(REPLIES))
    return Worker(client=github, provider=MockProvider(REPLIES), config=config, engine=None), github, pr


def job(pr: PullRequest, delivery: str) -> Job:
    return Job(pull_request=pr, delivery=delivery, installation=7)


def test_a_job_posts_one_comment_per_finding_in_order(tmp_path: Path) -> None:
    worker, github, pr = make_worker(tmp_path)
    assert run_job(worker, job(pr, "d41")) == 4
    assert [path for _, path, _, _ in github.comments] == [
        "src/review_assistant/findings/filter.py",
        "src/review_assistant/findings/filter.py",
        "src/review_assistant/cli.py",
        "src/review_assistant/config.py",
    ]


def test_a_redelivery_posts_nothing_twice(tmp_path: Path) -> None:
    worker, github, pr = make_worker(tmp_path)
    run_job(worker, job(pr, "d41"))
    assert run_job(worker, job(pr, "d41")) == 0
    assert len(github.comments) == 4


def test_a_second_push_is_served_from_the_cache_without_a_model_call(tmp_path: Path) -> None:
    worker, github, pr = make_worker(tmp_path)
    run_job(worker, job(pr, "d41"))
    calls = len(worker.provider.call_log) if isinstance(worker.provider, MockProvider) else 0
    pr.head_sha = "9999999"
    run_job(worker, job(pr, "d42"))
    assert github.diff_fetches == 1
    assert isinstance(worker.provider, MockProvider) and len(worker.provider.call_log) == calls


def test_the_lines_around_each_hunk_are_fetched(tmp_path: Path) -> None:
    worker, github, pr = make_worker(tmp_path)
    run_job(worker, job(pr, "d41"))
    hunks = sum(len(f.hunks) for f in parse(patch_text("three-files.patch")))
    assert len(github.file_fetches) == hunks
    assert {path for path, _ in github.file_fetches} == {
        "src/review_assistant/findings/filter.py",
        "src/review_assistant/cli.py",
        "src/review_assistant/config.py",
    }
