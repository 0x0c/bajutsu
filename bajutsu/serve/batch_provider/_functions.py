"""The batch-provider registry: register a kind, and dispatch a job naming it."""

from __future__ import annotations

from .batch_provider import BatchProvider

_PROVIDERS: dict[str, BatchProvider] = {}


def register(kind: str, provider: BatchProvider) -> None:
    """Register `provider` under `kind` so a `Job.batch` naming that `kind` dispatches to it."""
    _PROVIDERS[kind] = provider


def resolve(kind: str) -> BatchProvider:
    """Return the provider registered under `kind`, failing closed on an unknown one.

    Mirrors the mailbox / device-provider registries: an unknown `kind` is a clean config error raised
    here rather than a silent no-op that would let a cloud-batch job vanish.
    """
    if kind not in _PROVIDERS:
        allowed = ", ".join(repr(k) for k in _PROVIDERS) or "(none)"
        raise ValueError(f"unknown batch provider {kind!r}: registered kinds are {allowed}")
    return _PROVIDERS[kind]
