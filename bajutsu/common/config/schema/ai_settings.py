"""The `ai:` block as written: provider, model, endpoint, and key for the AI paths (BE-0047)."""

from __future__ import annotations

from pydantic import Field

from ._model import _Model
from .pricing_entry import PricingEntry


class AiSettings(_Model):
    """The `ai` block (BE-0047) — which provider/model/endpoint/key the AI paths use.

    `defaults.ai` is overridable per `targets.<name>.ai`. Keys never live here: `keyEnv` is the NAME
    of the env var holding the key, read at call time, so a secret never lands in the repo or an
    uploaded bundle. Every field is optional; an unset field falls back to the environment in the
    factory. `extra="forbid"` (from `_Model`) rejects a stray `apiKey:`-style field that would tempt
    a literal key into config.
    """

    # A registered provider name (BE-0104); anthropic is the default. The name is *not* validated
    # here: the deterministic core must not import the AI provider stack (BE-0112), and the registry
    # that owns the valid names lives in the periphery (`bajutsu.common.ai`). An unknown name fails closed
    # in that registry the first time an AI path resolves the provider, not at config load.
    provider: str | None = None
    model: str | None = None  # override the path's default model
    base_url: str | None = Field(default=None, alias="baseUrl")  # self-hosted gateway / proxy
    key_env: str | None = Field(default=None, alias="keyEnv")  # NAME of the env var (never the key)
    effort: str | None = None  # reasoning-effort level: low/medium/high/xhigh/max (claude-code)
    # AI output language for the model's generated prose (BE-0188): ja | en | auto. `auto` (the
    # default) keeps today's behavior — `record` follows the goal's language, `crawl` stays English.
    # Governs authoring/investigation prose only; never the deterministic run/CI verdict.
    language: str | None = None
    # AI usage/cost ledger (BE-0196), reporting only — never on the run/CI verdict. `usageLedger` is
    # the JSONL ledger path (unset = default under runs/, empty = disabled); `pricing` overrides the
    # shipped per-token rates, keyed by "provider/model" (e.g. "api-key/sonnet").
    usage_ledger: str | None = Field(default=None, alias="usageLedger")
    pricing: dict[str, PricingEntry] | None = None
