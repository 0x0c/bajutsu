"""The `selectOption` action: set a native select control to a given value."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class SelectOption(_Model):
    """`selectOption` action — set a native `<select>` to the option with the given value.

    Web-only: a `<select>` lives in the DOM but has no native counterpart on iOS / Android, so those
    backends refuse it (UnsupportedAction). `option` matches an option's *value* (not its visible
    label), mirroring the `value` assertion — which reads the `<select>`'s current value — so a
    picked option is directly assertable. A `<select>`'s dropdown is not in the DOM, so this is how a
    web `<select>` (e.g. the BE-0191 theme picker) is switched deterministically rather than by a
    coordinate click.
    """

    sel: Selector
    option: str
