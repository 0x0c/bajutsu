"""One organization's AI provider selection (BE-0229)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .provider_settings import ProviderSettings


@dataclass
class OrgProviderSettings:
    """One organization's AI provider selection (BE-0229): the active provider, its per-provider
    model/effort/region slots (BE-0183), and the output language (BE-0188).

    Replaces the single process-global selection with a per-org one, so a hosted multi-tenant serve
    resolves provider/model/effort per organization — whoever saved last no longer wins for everyone.
    `slots` maps a provider name to its remembered `ProviderSettings`; `provider` is the active one
    (empty = none selected, so resolution falls back to the launch env / default). `language` is the
    org-wide output-language override; blank/`auto` means the no-override default. Held in memory
    (keyed by org on `ServeState`) and, on a wired deployment, backed by the org's persistent store.
    """

    provider: str = ""
    slots: dict[str, ProviderSettings] = field(default_factory=dict)
    language: str = ""
