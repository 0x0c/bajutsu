"""The resolved `ai` block: which provider, model, endpoint, and key the AI paths use (BE-0047)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiConfig:
    """The resolved `ai` block (BE-0047): which provider/model/endpoint/key the AI paths use.

    Lives with the rest of the resolved config (not the AI client) so the deterministic core can
    read the block without importing the periphery AI stack (BE-0112). Every field is optional — an
    absent field falls back to the environment in the AI-client factory, so a config with no `ai:`
    block behaves exactly as before. `key_env` holds the NAME of the env var that carries the key,
    never the key itself.
    """

    provider: str | None = None
    model: str | None = None
    base_url: str | None = None  # self-hosted gateway / proxy for the Anthropic provider
    key_env: str | None = None  # name of the env var holding the API key (never the key)
    effort: str | None = None  # reasoning-effort level (low/medium/high/xhigh/max) where supported
    language: str | None = None  # AI output language for the generated prose (ja/en/auto), BE-0188
    # AI usage/cost ledger (BE-0196). `usage_ledger` is the JSONL path (None = default under runs/,
    # empty string = disabled); `pricing` overrides the shipped per-token rates, keyed by
    # "provider/model" with input/output/cacheWrite/cacheRead (USD per million tokens). Plain dicts,
    # not the ledger's own types, so the deterministic core stays free of the AI stack (BE-0112).
    usage_ledger: str | None = None
    pricing: dict[str, dict[str, float]] | None = None
