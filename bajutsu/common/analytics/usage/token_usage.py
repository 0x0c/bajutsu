"""An immutable snapshot of cumulative token counts across AI calls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsage:
    """An immutable snapshot of cumulative token counts across AI calls.

    `input_tokens` is the uncached input (the Anthropic API reports cache-written and
    cache-read input as the separate `cache_*` buckets), so the billed total is the sum of
    all four counts.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    calls: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.cache_write_tokens
            + self.cache_read_tokens
            + self.output_tokens
        )

    def __sub__(self, other: TokenUsage) -> TokenUsage:
        """The usage accrued between two snapshots (`after - before`)."""
        return TokenUsage(
            input_tokens=self.input_tokens - other.input_tokens,
            output_tokens=self.output_tokens - other.output_tokens,
            cache_write_tokens=self.cache_write_tokens - other.cache_write_tokens,
            cache_read_tokens=self.cache_read_tokens - other.cache_read_tokens,
            calls=self.calls - other.calls,
        )

    def __add__(self, other: TokenUsage) -> TokenUsage:
        """Field-wise sum of two snapshots (the per-category accumulator folds each call into its bucket)."""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            calls=self.calls + other.calls,
        )

    def render(self) -> str:
        """A one-line human summary, e.g.
        `AI usage: 1,234 tokens over 3 calls (900 in, 300 out; cache 20 write, 14 read)`."""
        cache = ""
        if self.cache_write_tokens or self.cache_read_tokens:
            cache = f"; cache {self.cache_write_tokens:,} write, {self.cache_read_tokens:,} read"
        plural = "" if self.calls == 1 else "s"
        return (
            f"AI usage: {self.total_tokens:,} tokens over {self.calls} call{plural} "
            f"({self.input_tokens:,} in, {self.output_tokens:,} out{cache})"
        )
