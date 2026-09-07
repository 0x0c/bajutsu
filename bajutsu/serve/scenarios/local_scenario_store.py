"""The on-disk scenario store: resolve an app to its directory, then scope to it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .local_scenario_scope import LocalScenarioScope
from .scenario_scope import ScenarioScope


class LocalScenarioStore:
    """Resolves an app to its on-disk scenarios dir, then scopes operations to it.

    The dir is resolved through a callable rather than captured, so a config opened from the UI
    after construction is reflected (the resolver reads the live serve state). The resolver takes the
    requesting session and acting org along with the app, because which configuration is bound is a
    per-session question (BE-0393 unit 2).
    """

    def __init__(self, resolve_dir: Callable[[str | None, str | None, str], Path | None]) -> None:
        self._resolve_dir = resolve_dir

    def scope(
        self, app: str | None, *, session: str | None = None, org: str = ""
    ) -> ScenarioScope | None:
        scn_dir = self._resolve_dir(app, session, org)
        return LocalScenarioScope(scn_dir) if scn_dir is not None else None
