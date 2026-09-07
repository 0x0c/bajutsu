"""The RunExecutor seam: how a created job gets executed (BE-0015 local/server parity).

`dispatch` is the single point where local and server hosting diverge. Locally each job runs
in-process on a daemon thread (`LocalExecutor`); the server backend instead enqueues the job for a
remote ``bajutsu worker`` (`DbQueueExecutor`, BE-0106). The execution body itself — boot, build,
run, stream — lives in `run_job` and is identical on both sides (locally the worker is just a
thread), so it stays put.
"""

from .local_executor import LocalExecutor
from .run_executor import RunExecutor

__all__ = ["LocalExecutor", "RunExecutor"]
