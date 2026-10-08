import json
from pathlib import Path

import pytest

from review_assistant.context.request import build_request
from review_assistant.diff.parser import parse
from review_assistant.models import Request
from review_assistant.providers.mock import MissingFixtureError, MockProvider, request_key
from tests.helpers import REPLIES, patch_text


def test_replays_a_recorded_reply_byte_for_byte() -> None:
    file = parse(patch_text("001-rename-helper.patch"))[0]
    request = build_request(file, "mock-review-1")
    recorded = json.loads((REPLIES / f"{request_key(request.text)}.json").read_text(encoding="utf-8"))
    reply = MockProvider(REPLIES).complete(request)
    assert reply.content == recorded["content"]
    assert (reply.input_tokens, reply.output_tokens) == (recorded["input_tokens"], recorded["output_tokens"])


def test_a_missing_fixture_names_the_key(tmp_path: Path) -> None:
    request = Request(text="never recorded", model="m", path="x.py")
    with pytest.raises(MissingFixtureError) as error:
        MockProvider(tmp_path).complete(request)
    assert request_key("never recorded") in str(error.value)


def test_the_call_log_records_every_request() -> None:
    provider = MockProvider(REPLIES)
    for file in parse(patch_text("three-files.patch")):
        provider.complete(build_request(file, "mock-review-1"))
    assert [r.path for r in provider.call_log] == [
        "src/review_assistant/findings/filter.py",
        "src/review_assistant/cli.py",
        "src/review_assistant/config.py",
    ]
