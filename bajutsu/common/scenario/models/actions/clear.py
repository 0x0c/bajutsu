"""The `clear` action: empty a field's entire content (BE-0265)."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class Clear(_Model):
    """`clear` action — clear the field's entire current content (BE-0265).

    On a backend that can select the field's content (`Capability.TEXT_SELECTION`), realized as a
    platform select-all followed by one backspace: a backspace with an active selection removes the
    whole selection, so this is correct regardless of where the focusing tap lands the caret, and
    unaffected by whether the reported `value` matches the field's real deletable length (a
    secure/password field, a currency mask). The select-all's effect is unverifiable from the
    selector-based API a backend exposes it through, so a read-back `value` check follows it; if the
    field is not empty (a select-all chord the platform mapped to something else, e.g.), the counted
    backspace run below finishes the job rather than reporting success after deleting only one
    character. A backend with no select-all handle goes straight to that counted run: one backspace
    per character of the field's reported `value`, where a masked/reformatted `value` can still cause
    an under- or over-delete. Verify the outcome with a `value` assertion when it matters.
    """

    into: Selector
