import json
from pathlib import Path

from typer.testing import CliRunner

from review_assistant.cli import app
from review_assistant.config import Config
from review_assistant.diff.parser import parse
from review_assistant.ledger.db import connect, rows
from review_assistant.providers.mock import MockProvider
from review_assistant.review import review_files
from tests.helpers import PATCHES, REPLIES, patch_text

runner = CliRunner()


def config_file(tmp_path: Path, **values: object) -> Path:
    file = tmp_path / ".review-assistant.yml"
    lines = [f"ledger_path: {(tmp_path / 'ledger.sqlite').as_posix()}", f"replies_dir: {REPLIES.as_posix()}"]
    lines += [f"{k}: {v}" for k, v in values.items()]
    file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return file


def test_example_1_the_table_and_the_cost_line(tmp_path: Path) -> None:
    args = ["review", str(PATCHES / "001-rename-helper.patch"), "--config", str(config_file(tmp_path))]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert "src/review_assistant/web/worker.py:85" in result.output
    assert "cost:" in result.output and "cents" in result.output


def test_example_2_json_findings_carry_new_file_lines(tmp_path: Path) -> None:
    config = config_file(tmp_path)
    args = ["review", str(PATCHES / "three-files.patch"), "--format", "json", "--config", str(config)]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    findings = json.loads(result.stdout)
    assert {tuple(sorted(f)) for f in findings} == {("line", "message", "path", "severity")}
    assert {(f["path"], f["line"]) for f in findings} == {
        ("src/review_assistant/findings/filter.py", 42),
        ("src/review_assistant/findings/filter.py", 57),
        ("src/review_assistant/cli.py", 18),
        ("src/review_assistant/config.py", 9),
    }


def test_example_3_the_floor_hides_findings_but_the_ledger_bills_the_whole_request(tmp_path: Path) -> None:
    config = config_file(tmp_path, severity_floor="high")
    args = ["review", str(PATCHES / "three-files.patch"), "--format", "json", "--config", str(config)]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert {f["severity"] for f in json.loads(result.stdout)} == {"high", "critical"}
    ledger = rows(connect(tmp_path / "ledger.sqlite"))
    assert len(ledger) == 1 and ledger[0].cents >= 1


def test_example_4_three_files_make_three_requests(tmp_path: Path) -> None:
    provider = MockProvider(REPLIES)
    config = Config(ledger_path=str(tmp_path / "ledger.sqlite"))
    review_files(parse(patch_text("three-files.patch")), config, provider, None)
    assert len(provider.call_log) == 3


def test_example_5_files_over_the_budget_are_dropped_and_reported(tmp_path: Path) -> None:
    config = config_file(tmp_path, model_limit=8192, reserved_for_reply=7700)
    result = runner.invoke(app, ["review", str(PATCHES / "three-files.patch"), "--config", str(config)])
    assert result.exit_code == 0, result.output
    assert "dropped src/review_assistant/config.py: over the token budget" in result.output


def test_every_fixture_patch_parses_and_reviews(tmp_path: Path) -> None:
    for patch in sorted(PATCHES.glob("*.patch")):
        args = ["review", str(patch), "--format", "json", "--config", str(config_file(tmp_path))]
        result = runner.invoke(app, args)
        assert result.exit_code == 0, f"{patch.name}: {result.output}"
