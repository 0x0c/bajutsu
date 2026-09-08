"""The `clear` action: empty a field's entire content (BE-0265)."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class Clear(_Model):
    """`clear` action — clear the field's entire current content (backspace-equivalent; BE-0265).

    Realized as one backspace per character of the field's reported `value`, so it stays agnostic to
    what the field held. That count comes from the accessibility `value`, which equals the character
    count for a plain text field; a field whose `value` is masked or reformatted (a secure/password
    field, a currency mask) can report a length that differs from what is deletable, so `clear` may
    under- or over-delete there. Backend actuation fidelity for such fields is build-time triage
    (per *Detailed design*); verify the outcome with a `value` assertion when it matters.
    """

    into: Selector
