from pathlib import Path

from sqlalchemy import inspect

from review_assistant.ledger.db import connect, record_review, row_for, rows


def test_connect_migrates_an_empty_file_to_the_current_schema(tmp_path: Path) -> None:
    engine = connect(tmp_path / "ledger.sqlite")
    columns = {c["name"] for c in inspect(engine).get_columns("reviews")}
    expected = {"provider", "model", "pull_request", "delivery", "input_tokens", "output_tokens", "cents"}
    assert expected <= columns


def test_a_review_inserts_one_row_with_its_cost(tmp_path: Path) -> None:
    engine = connect(tmp_path / "ledger.sqlite")
    record_review(
        engine,
        provider="mock",
        model="mock-review-1",
        input_tokens=6120,
        output_tokens=412,
        cents=3,
        pull_request=118,
        delivery="d41",
    )
    found = rows(engine)
    assert len(found) == 1
    assert (found[0].cents, found[0].pull_request, found[0].delivery) == (3, 118, "d41")
    latest = row_for(engine, 118)
    assert latest is not None and latest.input_tokens == 6120
    assert row_for(engine, 119) is None


def test_a_limit_returns_the_newest_rows_in_order(tmp_path: Path) -> None:
    engine = connect(tmp_path / "ledger.sqlite")
    for cents in (1, 2, 3):
        record_review(engine, provider="mock", model="m", input_tokens=1, output_tokens=1, cents=cents)
    assert [r.cents for r in rows(engine, limit=2)] == [2, 3]
    assert [r.cents for r in rows(engine)] == [1, 2, 3]
