"""The error raised when a screen cannot be probed for scoring — config, not a crash."""

from __future__ import annotations


class DoctorProbeError(RuntimeError):
    """The screen can't be probed for scoring — a fixable config error, not a crash.

    Raised only for the config-level "can't even attempt the probe" case (e.g. a web target
    with no baseUrl). The caller maps it to its own surface (CLI: `typer.Exit(2)`; serve:
    `ValueError`). Device/reachability faults keep raising their transport error (`DeviceError`,
    a Playwright error), which the callers already handle distinctly.
    """
