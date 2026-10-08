"""Cost arithmetic for one review."""

from __future__ import annotations

# Cents per million tokens, input and output, per model. The mock's prices are the ones the course's
# worked examples use, so a review of the three-file fixture costs three cents.
PRICES: dict[str, tuple[int, int]] = {
    "mock-review-1": (300, 2500),
    "claude-sonnet-5": (300, 1500),
    "claude-haiku-4-5-20251001": (100, 500),
    "gpt-5": (125, 1000),
}
DEFAULT_PRICE = (300, 1500)


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
    micro = input_tokens * input_cents_per_million + output_tokens * output_cents_per_million
    return (micro + 500_000) // 1_000_000


def cost_for(model: str, input_tokens: int, output_tokens: int) -> int:
    """Bill a review on a named model, falling back to the default price list."""
    input_price, output_price = PRICES.get(model, DEFAULT_PRICE)
    return review_cost_cents(input_tokens, output_tokens, input_price, output_price)
