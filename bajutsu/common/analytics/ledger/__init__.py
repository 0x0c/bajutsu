"""Attributed, persistent AI usage/cost ledger (BE-0196).

`bajutsu.common.analytics.usage` keeps a flat, in-memory token total that dies with the process. This module makes
that history durable and attributed: one JSONL line per AI call, tagged with what the tokens were
spent on (command, provider, model, scenario, step) and priced in dollars where the provider has
per-token pricing. It is the raw material the usage dashboard reads.

Reporting only — nothing here runs on the deterministic `run` / CI verdict, and recording is
best-effort: `bajutsu.common.analytics.usage.record` calls `emit` inside a swallow-everything guard, so a full disk
never breaks an AI path. Following the operational-logging rules (BE-0055 / BE-0047), the ledger
stores counts, prices, and labels only — never prompt or response content.
"""

from ._functions import _ATTRIBUTION as _ATTRIBUTION
from ._functions import _DEFAULT_PRICING as _DEFAULT_PRICING
from ._functions import (
    DEFAULT_LEDGER_PATH,
    PricingTable,
    attributed,
    bind_command,
    compute_cost,
    configure,
    configure_from_ai_config,
    current_attribution,
    default_pricing_table,
    emit,
    pricing_table_from_config,
    read_events,
    reset,
    resolve_ledger_path,
)
from ._functions import _find_pricing as _find_pricing
from .attribution import Attribution
from .jsonl_ledger import JsonlLedger
from .pricing import Pricing
from .usage_event import LEDGER_SCHEMA_VERSION, UsageEvent

__all__ = [
    "DEFAULT_LEDGER_PATH",
    "LEDGER_SCHEMA_VERSION",
    "Attribution",
    "JsonlLedger",
    "Pricing",
    "PricingTable",
    "UsageEvent",
    "attributed",
    "bind_command",
    "compute_cost",
    "configure",
    "configure_from_ai_config",
    "current_attribution",
    "default_pricing_table",
    "emit",
    "pricing_table_from_config",
    "read_events",
    "reset",
    "resolve_ledger_path",
]
