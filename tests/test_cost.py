from review_assistant.ledger.cost import cost_for, review_cost_cents


def test_a_typical_review() -> None:
    assert review_cost_cents(1000, 500, 300, 1500) == 1


def test_nothing_used_costs_nothing() -> None:
    assert review_cost_cents(0, 0, 300, 1500) == 0


def test_a_million_input_tokens() -> None:
    assert review_cost_cents(1_000_000, 0, 300, 1500) == 300


def test_cost_for_falls_back_to_the_default_price() -> None:
    assert cost_for("some-unknown-model", 1_000_000, 0) == 300
