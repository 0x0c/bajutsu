"""One dimension value's aggregate: its calls, tokens, and dollar cost."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UsageRow:
    """One dimension value's aggregate — its calls, tokens, and dollar cost.

    `cost` sums only the priced calls; `priced_calls` / `unpriced_calls` split the total so a group
    with no per-token price reads as unpriced (`has_price` False → the view shows "—") rather than a
    fabricated `$0.00`.
    """

    key: str  # the provider / model / command / scenario value; None coalesced to "(unknown)"
    calls: int
    tokens: int
    cost: float  # sum of the priced calls' cost; 0.0 when none in the group was priced
    priced_calls: int
    unpriced_calls: int

    @property
    def has_price(self) -> bool:
        """Whether any call in this group carried a per-token price (else the view shows "—")."""
        return self.priced_calls > 0
