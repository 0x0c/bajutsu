"""One AI provider's remembered model, effort, and region for a serve session (BE-0183)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderSettings:
    """One AI provider's remembered model/effort/region for the serve session (BE-0183).

    Scopes the fields to the provider they belong to, so switching the Settings dropdown no longer
    overwrites what was set for the provider left behind. `region` applies to `bedrock` only; the
    SDK/CLI providers leave it empty. Held in memory and materialized into env vars; on local serve
    it is also persisted through `ProviderSettingsManager.store` so a saved choice survives a restart
    (BE-0184).
    """

    model: str = ""
    effort: str = ""
    region: str = ""
