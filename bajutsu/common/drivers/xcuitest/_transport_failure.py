"""One channel attempt's transport failure, tagged with whether the request reached the runner."""

from __future__ import annotations


class _TransportFailure(Exception):
    """A transport-level failure from one channel attempt, tagged with whether the request reached the runner.

    Internal to the retry seam (BE-0207): `_with_retry` reads `delivered` to decide whether re-issuing
    the call could double-apply a side-effecting write. It never escapes the module — an exhausted or
    retry-ineligible failure is turned into the caller-facing `XcuitestChannelError`.

    `hung` splits the delivered case by *how* it failed (BE-0354): a response timeout means the runner
    accepted the request and never answered, while a reset or a refused connection means it stopped
    serving. Only the former identifies a wedged automation session, so the two cannot share one tag.
    """

    def __init__(self, message: str, *, delivered: bool, hung: bool = False) -> None:
        super().__init__(message)
        self.delivered = delivered
        self.hung = hung
