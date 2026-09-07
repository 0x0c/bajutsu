"""The seam an app is mapped to its scenario scope through."""

from __future__ import annotations

from typing import Protocol

from .scenario_scope import ScenarioScope


class ScenarioStore(Protocol):
    """Maps an app to its scenario scope."""

    def scope(
        self, app: str | None, *, session: str | None = None, org: str = ""
    ) -> ScenarioScope | None:
        """The scope for *app*, or None when the app has no scenarios dir.

        *session* and *org* name the request asking (BE-0393 unit 2). A scenarios dir is resolved
        against the bound configuration, and a binding is per session and acting org, so the store's
        own resolution is where the request hands that pair in — the store is built once per
        deployment, with no handler in scope. Both default to "no session", which reads the
        deployment's fallback binding: the answer for a shared-token caller and for the boot-time
        readers that have no request at all.
        """
