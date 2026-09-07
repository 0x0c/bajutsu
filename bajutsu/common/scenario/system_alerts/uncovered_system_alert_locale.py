"""The error raised for a prompt and choice under a language the table does not cover."""

from __future__ import annotations


class UncoveredSystemAlertLocale(ValueError):
    """A `prompt` / `choice` pair was asked for under a language the table does not cover.

    Raised rather than guessed at: a wrong label would tap nothing (or, worse, the other button),
    and BE-0320 exists to remove exactly that kind of accident.
    """
