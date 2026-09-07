"""The seam an already-created job is executed through, asynchronously."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bajutsu.serve.state import Job, ServeState


class RunExecutor(Protocol):
    """Arranges for an already-created `Job` to be executed asynchronously."""

    def dispatch(self, state: ServeState, job: Job) -> None:
        """Arrange for *job* to be executed asynchronously."""
