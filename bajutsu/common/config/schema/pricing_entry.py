"""One provider-and-model pair's rates under `ai.pricing`, in USD per million tokens (BE-0196)."""

from __future__ import annotations

from pydantic import Field

from ._model import _Model


class PricingEntry(_Model):
    """Per-token rates for one `(provider, model)` in `ai.pricing` (BE-0196), USD per million tokens.

    Overrides a shipped default. `cacheWrite` / `cacheRead` default to 0 for a provider that does
    not price cache separately, so an entry may name only `input` / `output`.
    """

    input: float
    output: float
    cache_write: float = Field(default=0.0, alias="cacheWrite")
    cache_read: float = Field(default=0.0, alias="cacheRead")
