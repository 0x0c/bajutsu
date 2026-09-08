"""A durable record of a scheduled cloud run, so a re-leased worker resumes it."""

from __future__ import annotations

from typing import Protocol


class BatchCheckpoint(Protocol):
    """A durable record of a cloud-batch run's scheduled ARN, so a re-leased worker resumes it (Unit 5).

    A batch run's poll can span the 150-minute hard cap. On the hosted DB backend a worker persists the
    run ARN through this seam the moment the run is scheduled; a worker that picks the same job up again
    after a restart loads it and resumes polling that run instead of resubmitting — the long poll
    survives a serve restart rather than orphaning the run (and its reserved device).
    """

    def load(self) -> str | None:
        """The scheduled run ARN persisted for this job, or None if it is not yet scheduled."""

    def save(self, run_arn: str) -> None:
        """Persist the scheduled run ARN so a restart resumes polling it."""
