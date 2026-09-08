"""The coercions a scenario's YAML shorthands are read through."""

from __future__ import annotations

from typing import Any


def _coerce_system_alert_handling(v: Any) -> Any:
    """`true` is the empty policy (on, no declarations); everything else reaches the union as-is."""
    return {} if v is True else v
