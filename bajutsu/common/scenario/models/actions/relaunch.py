"""The `relaunch` action: restart the app process, optionally with a new launch environment."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class Relaunch(_Model):
    """`relaunch` action — restart the app process, optionally overriding its launch env/args."""

    env: dict[str, str] | None = None
    args: list[str] | None = None
