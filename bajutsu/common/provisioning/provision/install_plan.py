"""What provisioning would install for a backend, before it installs anything."""

from __future__ import annotations

from dataclasses import dataclass

from bajutsu.common.provisioning.requirements import Tool


@dataclass(frozen=True)
class InstallPlan:
    """The extras and external tools a config resolves to needing.

    ``tools`` may include Extra-backed entries (e.g. the web `playwright` package): those are covered
    by the ``extras`` sync, so ``provision`` takes no separate action for them.
    """

    extras: tuple[str, ...]
    tools: tuple[Tool, ...]

    @property
    def is_empty(self) -> bool:
        return not self.extras and not self.tools
