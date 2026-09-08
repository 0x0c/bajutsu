"""The in-process executor, one daemon thread per job — serve's default."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bajutsu.serve.state import Job, ServeState


class LocalExecutor:
    """Runs each job in-process on a daemon thread — the default for `bajutsu serve`."""

    def dispatch(self, state: ServeState, job: Job) -> None:
        from bajutsu.serve.jobs import run_job  # local import breaks the jobs↔executor cycle

        threading.Thread(target=run_job, args=(state, job), daemon=True).start()
