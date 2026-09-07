"""One AI call's durable record: its attribution, token counts, and computed cost."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from bajutsu.common.analytics.usage import TokenUsage

# Bump when the on-disk record shape changes incompatibly; readers key off it to stay
# forward-compatible (an older line is still parseable — see `UsageEvent.from_record`).
LEDGER_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class UsageEvent:
    """One AI call's durable record: its attribution, token counts, and computed dollar cost."""

    ts: str  # UTC ISO-8601 timestamp
    command: str | None
    provider: str | None
    model: str | None
    scenario: str | None
    step: str | None
    usage: TokenUsage
    cost: float | None

    def to_record(self) -> dict[str, Any]:
        """The versioned, JSON-serializable dict written as one ledger line."""
        return {
            "v": LEDGER_SCHEMA_VERSION,
            "ts": self.ts,
            "command": self.command,
            "provider": self.provider,
            "model": self.model,
            "scenario": self.scenario,
            "step": self.step,
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "cache_write_tokens": self.usage.cache_write_tokens,
            "cache_read_tokens": self.usage.cache_read_tokens,
            "calls": self.usage.calls,
            "cost": self.cost,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> UsageEvent:
        """Parse one ledger line. Missing fields degrade gracefully (older/partial lines stay readable)."""
        return cls(
            ts=record["ts"],
            command=record.get("command"),
            provider=record.get("provider"),
            model=record.get("model"),
            scenario=record.get("scenario"),
            step=record.get("step"),
            usage=TokenUsage(
                input_tokens=record.get("input_tokens", 0),
                output_tokens=record.get("output_tokens", 0),
                cache_write_tokens=record.get("cache_write_tokens", 0),
                cache_read_tokens=record.get("cache_read_tokens", 0),
                calls=record.get("calls", 0),
            ),
            cost=record.get("cost"),
        )
