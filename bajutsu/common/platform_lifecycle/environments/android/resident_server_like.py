"""The lease-lifecycle slice of the resident server the Android environment drives."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bajutsu.common.backend_cli.adb_resident import ResidentChannel


@runtime_checkable
class ResidentServerLike(Protocol):
    """The lease-lifecycle slice of `bajutsu.common.backend_cli.adb_resident.ResidentServer` the environment drives."""

    def start(self) -> ResidentChannel: ...

    def stop(self) -> None: ...
