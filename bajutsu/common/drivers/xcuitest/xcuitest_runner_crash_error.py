"""The error raised when the runner died mid-run and stayed unreachable (BE-0287)."""

from __future__ import annotations

from bajutsu.common.drivers import base

from .xcuitest_channel_error import XcuitestChannelError


class XcuitestRunnerCrashError(XcuitestChannelError, base.BackendCrashError):
    """The runner died mid-run: the loopback channel stayed unreachable past the transient-retry budget (BE-0287).

    Also a `base.BackendCrashError`, so the backend-agnostic run pipeline recovers it uniformly:
    it discards the dead lease, cold-respawns a fresh runner, and re-runs the whole scenario (bounded).

    A crash outlives the BE-0207 retry (a sub-second blip smoother), so it is kept distinct from both a
    transient blip and a decoded test outcome: it names an honest "the runner crashed" failure, so a
    lost two-finger gesture never masquerades as an assertion mismatch (`actual='idle'`). `delivered`
    records whether the failed call had reached the runner, so the crash-recovery layer can tell a
    safe-to-re-issue read from a write that must not be re-applied. `hung` narrows `delivered` further
    (BE-0354): the request reached the runner and no response ever came, the one shape that identifies
    a wedged automation session rather than a runner that died.
    """

    def __init__(
        self, message: str, *, method: str = "", delivered: bool = False, hung: bool = False
    ) -> None:
        super().__init__(message)
        self.method = method
        self.delivered = delivered
        self.hung = hung
