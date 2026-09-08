"""The aggregate read of the jobs table behind the metrics endpoint (BE-0169)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class JobMetrics:
    """An aggregate read of the jobs table for the ``/metrics`` endpoint (BE-0169).

    Every field is derived from rows the lease path already maintains — this adds no bookkeeping.
    Ages are seconds relative to the server clock at snapshot time; ``leased_at`` doubles as the
    worker's last-heartbeat timestamp (the worker renews it on its heartbeat interval), so its age
    is the liveness signal.
    """

    queued_by_org: dict[str, int]  # org_id -> jobs waiting in the queue
    leased_by_org: dict[str, int]  # org_id -> jobs leased to a worker (in flight)
    # worker_id -> seconds since its freshest lease renewal; rising past the lease timeout = dead
    heartbeat_age_by_worker: dict[str, float]
    # Seconds since the oldest in-flight (leased) job was *enqueued* (created_at), so it includes
    # the time it waited in the queue before the lease — a slow / stuck-run signal; 0.0 if none
    oldest_in_flight_seconds: float
    # Queued jobs no *live* worker can serve — their required capabilities are a subset of no live
    # worker's advertised set (BE-0166). A rising count is the operator's "add a worker with X"
    # signal; such a job stays queued rather than being leased to an incompatible worker or dropped.
    unroutable_queued: int = 0
