"""The defaults a collector falls back to when the app reports no transitions."""

from __future__ import annotations

from collections.abc import Callable

from .screen_transition import ScreenTransition

# Returns the screen-transition events observed so far, each with the collector's receive time
# (its own monotonic clock, the same domain the readiness gate and the `settled` wait already poll
# in) — for `await_ready` / `_wait_settled` (BE-0310) to consult as a read-only signal. Mirrors
# `Collector.snapshot_timed()`'s shape (below), not the untimed `orchestrator.types.NetworkSource`:
# both readiness and settled need the receive time itself (to bound "since this wait started" /
# compute the quiescence window), unlike a `request` assertion, which only needs exchange content.
# Kept here (not in `orchestrator`) since the readiness gate lives in `platform_lifecycle`, outside
# the orchestrator package.
TransitionSource = Callable[[], list[tuple[ScreenTransition, float]]]
