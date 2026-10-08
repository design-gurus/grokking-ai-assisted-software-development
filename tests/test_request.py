import pytest

from review_assistant.context.request import INSTRUCTIONS, build_request
from review_assistant.diff.parser import parse
from tests.helpers import patch_text


def test_the_request_is_the_instructions_then_the_rendered_file() -> None:
    file = parse(patch_text("001-rename-helper.patch"))[0]
    request = build_request(file, "mock-review-1")
    assert request.text.startswith(INSTRUCTIONS + "\n\nFile: src/review_assistant/web/worker.py")
    assert "```diff" in request.text
    assert request.untrusted is None


def test_an_unknown_template_version_is_refused() -> None:
    file = parse(patch_text("001-rename-helper.patch"))[0]
    with pytest.raises(ValueError):
        build_request(file, "m", 2)
