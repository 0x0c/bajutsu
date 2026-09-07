"""How a suite's network assertions cover the endpoints its runs actually hit."""

from __future__ import annotations

from dataclasses import dataclass

# --- endpoint coverage: observed traffic (network.json) vs the endpoints the suite asserts on ---


@dataclass(frozen=True)
class EndpointCoverage:
    """How a suite's network assertions cover the endpoints its runs actually hit."""

    observed: list[str]  # distinct "METHOD path" seen across the run set (sorted)
    asserted: list[str]  # observed endpoints some declared matcher matches
    unasserted: list[str]  # observed endpoints no matcher matches — untested traffic
    declared_unobserved: list[str]  # matcher labels that matched no observed exchange
    coverage: float  # asserted / observed (1.0 when nothing was observed)
