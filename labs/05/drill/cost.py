"""The tests-first drill from the testing module's bar lesson.

Write labs/05/drill/test_cost.py from the docstring below before you write the body. Five cases:
the half cent, just under a cent, far under, zero, and the worked example from the logs. Run them,
watch all five fail, then implement, then watch them pass. Then: mutmut run --paths-to-mutate labs/05/drill/cost.py
"""


def review_cost_cents(
    input_tokens: int,
    output_tokens: int,
    input_cents_per_million: int,
    output_cents_per_million: int,
) -> int:
    """Cost of one review in whole cents, rounded half up.

    Prices are in cents per million tokens, so 1,000 input tokens at
    500 cents per million is half a cent, which rounds to 1.
    """
    raise NotImplementedError("write the tests first, then this body")
