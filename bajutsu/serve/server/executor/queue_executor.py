"""The executor that dispatches a job by enqueuing its spec for a remote worker."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bajutsu.serve.server.worker_job import execute_job_spec, job_spec

from .queue import Queue

if TYPE_CHECKING:
    from bajutsu.serve.state import Job, ServeState


class QueueExecutor:
    """Dispatches a job by enqueuing its spec for a remote worker (the `RunExecutor` seam)."""

    def __init__(self, queue: Queue) -> None:
        self._queue = queue

    def dispatch(self, state: ServeState, job: Job) -> None:  # noqa: ARG002  # RunExecutor shape
        # The worker reconstructs the job from this spec and runs `run_job`; `state` stays on the
        # control plane (its popen/simctl/cwd are worker-side concerns).
        self._queue.enqueue(execute_job_spec, job_spec(job))
