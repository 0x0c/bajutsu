"""The human-readable channel for the CLI, value-masked like the JSON one."""

from __future__ import annotations

import logging

from bajutsu.common.evidence.redaction import Redactor


class _TextFormatter(logging.Formatter):
    """Human-readable single line for the CLI, value-masked like the JSON channel.

    A traceback is appended to the *same* line with its newlines escaped, matching the JSON
    channel's one-record-per-line contract — the stdlib default (bare `super().format`) instead
    appends the exception/stack text after a real ``\\n``, spanning as many lines as the traceback
    has frames.
    """

    def __init__(self, static: Redactor) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s %(message)s")
        self._static = static

    def format(self, record: logging.LogRecord) -> str:
        exc_info, stack_info = record.exc_info, record.stack_info
        record.exc_info = record.stack_info = None
        try:
            line = super().format(record)
        finally:
            record.exc_info, record.stack_info = exc_info, stack_info
        if exc_info:
            line += " exc=" + self.formatException(exc_info).replace("\n", "\\n")
        if stack_info:
            line += " stack=" + self.formatStack(stack_info).replace("\n", "\\n")
        # Imported in the method, not at module load: `_functions` registers this
        # formatter, and rule 5 breaks the cycle the split creates on this side.
        from ._functions import _mask_values

        return _mask_values(self._static, line)
