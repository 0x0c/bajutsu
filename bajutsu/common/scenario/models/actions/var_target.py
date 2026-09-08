"""Where a producing step writes its value: the `${vars.*}` slot it names."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class VarTarget(_Model):
    """`into: { var: <name> }` — the `${vars.<name>}` slot a step writes its produced value to."""

    var: str
