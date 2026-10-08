from review_assistant.findings.filter import apply_filters, apply_floor, in_diff, meets_floor
from review_assistant.models import FileDiff, Finding, Hunk


def finding(severity: str, line: int = 1, path: str = "a.py") -> Finding:
    return Finding(path=path, line=line, severity=severity, message=severity)


def test_a_higher_severity_meets_a_lower_floor() -> None:
    assert meets_floor("critical", "low")


def test_a_lower_severity_does_not_meet_a_higher_floor() -> None:
    assert not meets_floor("low", "high")


def test_apply_floor_keeps_order() -> None:
    findings = [finding("low"), finding("critical"), finding("medium"), finding("critical")]
    kept = apply_floor(findings, "medium")
    assert [f.severity for f in kept] == ["critical", "medium", "critical"]


def test_in_diff_drops_lines_the_diff_does_not_show() -> None:
    file = FileDiff(path="a.py", patch="", hunks=[Hunk(10, 4, 10, 5, lines=[" x", "+y", " z", "+w", " v"])])
    findings = [finding("high", 12), finding("high", 30), finding("high", 12, "b.py")]
    assert [f.line for f in in_diff(findings, file)] == [12]


def test_ignored_path_is_dropped() -> None:
    f = [Finding(path="vendor/x.py", line=1, severity="critical", message="m")]
    assert apply_filters(f, "low", ["vendor/*"]) == []


def test_ignore_runs_before_floor_and_keeps_order() -> None:
    f = [
        Finding(path="a.py", line=1, severity="high", message="a"),
        Finding(path="b.py", line=1, severity="low", message="b"),
        Finding(path="c.py", line=1, severity="high", message="c"),
    ]
    assert [x.path for x in apply_filters(f, "medium", [])] == ["a.py", "c.py"]
