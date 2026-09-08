"""The slice of `subprocess.Popen` the resident server's lifecycle needs, small enough to fake."""

from __future__ import annotations

from typing import Protocol


class _Process(Protocol):
    """The slice of `subprocess.Popen` the lifecycle needs — small enough for tests to fake."""

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def poll(self) -> int | None: ...

    def wait(self, timeout: float | None = None) -> int: ...
