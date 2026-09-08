"""One provider-and-model pair's per-token rates, in US dollars per million tokens."""

from __future__ import annotations

from dataclasses import dataclass

from bajutsu.common.analytics.usage import TokenUsage


@dataclass(frozen=True)
class Pricing:
    """Per-token rates for one `(provider, model)`, expressed in US dollars per million tokens.

    Per-million (not per-token) because that is how providers publish list prices, so a config
    override reads the same as the vendor's page. `cost` converts back to an absolute dollar figure.
    """

    input_usd_per_mtok: float
    output_usd_per_mtok: float
    cache_write_usd_per_mtok: float
    cache_read_usd_per_mtok: float

    def cost(self, u: TokenUsage) -> float:
        """The dollar cost of *u* at these rates."""
        return (
            u.input_tokens * self.input_usd_per_mtok
            + u.output_tokens * self.output_usd_per_mtok
            + u.cache_write_tokens * self.cache_write_usd_per_mtok
            + u.cache_read_tokens * self.cache_read_usd_per_mtok
        ) / 1_000_000
