import pytest

from review_assistant.findings.parse import ReplyFormatError, parse_reply


def test_parses_a_json_array() -> None:
    content = '[{"line": 4, "severity": "high", "message": "m"}]'
    found = parse_reply(content, "a.py")
    assert len(found) == 1
    assert (found[0].path, found[0].line, found[0].severity) == ("a.py", 4, "high")


def test_strips_a_code_fence() -> None:
    content = '```json\n[{"line": 2, "severity": "low", "message": "m"}]\n```'
    assert len(parse_reply(content, "a.py")) == 1


def test_skips_malformed_items_and_keeps_the_rest() -> None:
    content = (
        '[{"line": "4", "severity": "high", "message": "m"}, '
        '{"line": 0, "severity": "low", "message": "m"}, '
        '{"line": 3, "severity": "urgent", "message": "m"}, '
        '{"line": 5, "severity": "low", "message": "ok"}]'
    )
    assert [f.line for f in parse_reply(content, "a.py")] == [5]


def test_not_json_raises() -> None:
    with pytest.raises(ReplyFormatError):
        parse_reply("Sure! Here are the findings:", "a.py")
