"""The error raised when a backend's driver process crashed and could not be recovered."""

from __future__ import annotations


class BackendCrashError(RuntimeError):
    """The backend's driver process crashed mid-scenario and could not be recovered in place.

    Distinct from a test outcome and from a transient blip a driver's own retry absorbs: it names an
    honest "the backend died" — the resident XCUITest runner's XCTest host, an adb server, a browser
    process — where the crash outlived the driver's in-place recovery budget, so the current
    scenario's state is gone. The run pipeline treats it as backend infrastructure, not a verdict
    (prime directive 1): it discards the dead lease, leases a fresh device (a cold respawn), and
    re-runs the whole scenario from the start, bounded — a genuinely crash-inducing app still fails
    loudly once the retries are spent, so flakiness is never absorbed into a pass (BE-0049). Backends
    raise a subclass (e.g. `XcuitestRunnerCrashError`); the pipeline catches this base so the recovery
    stays backend-agnostic (prime directive 3).
    """
