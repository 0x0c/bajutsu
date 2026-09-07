"""A human's answer to a handoff: values supplied, an action performed, or a cancel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class HandoffResponse:
    """A human's answer to a handoff: values supplied, an action performed, or a cancel.

    `values` are literal strings the human supplied (e.g. a one-time password); `acted` says
    the human operated the device and the loop should re-observe from the new screen;
    `cancelled` ends the record cleanly. The substrate carries these and resumes by
    re-observation — a child item decides what, if anything, to record from them.
    """

    values: list[str] = field(default_factory=list)
    acted: bool = False
    cancelled: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandoffResponse:
        """Build a response from a decoded payload, coercing types — the one authority for turning
        an untrusted map (a stdin line, a `respond-human` POST body) into a response.

        A bare `values` string (or any non-list) is wrapped as a single value, never iterated
        character by character — so `{"values": "123456"}` supplies one code, not six.
        """
        raw = data.get("values")
        if raw is None:
            values: list[str] = []
        elif isinstance(raw, (list, tuple)):
            values = [str(v) for v in raw]
        else:
            values = [str(raw)]
        return cls(
            values=values,
            acted=bool(data.get("acted", False)),
            cancelled=bool(data.get("cancelled", False)),
        )

    @property
    def kind(self) -> Literal["cancel", "value", "acted"]:
        """The single outcome, resolving precedence so consumers never hand-order the checks: a
        cancel wins over everything, then a value response, then a bare acted flag."""
        if self.cancelled:
            return "cancel"
        return "value" if self.values else "acted"
