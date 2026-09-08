"""The single-line JSON channel: one object per record, correlation ids included."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from bajutsu.common.evidence.redaction import Redactor

from ._shared import _CONTEXT_KEYS


class _JsonFormatter(logging.Formatter):
    """Single-line JSON: ``ts, level, logger, event?, msg, <correlation ids?>, <extras?>, exc_info?``.

    Value-masking is applied to the whole serialized line, so a known secret value is scrubbed
    wherever it lands, including inside a non-string field stringified by ``json.dumps``.

    A traceback (``exc_info=True`` / ``logger.exception``) is rendered into its own ``exc_info``
    field rather than appended as raw text: ``json.dumps`` escapes its newlines, so the record
    stays exactly one line — the multi-line stdlib default would otherwise split a JSON stream
    across several unparseable lines.
    """

    def __init__(self, static: Redactor) -> None:
        super().__init__()
        self._static = static

    def format(self, record: logging.LogRecord) -> str:
        # Imported in the method, not at module load: `_functions` registers this formatter, and
        # rule 5 breaks the cycle the split creates on this side.
        from ._functions import _extras, _mask_values

        line: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        event = getattr(record, "event", None)
        if event is not None:
            line["event"] = event
        line["msg"] = record.getMessage()
        for key, _ in _CONTEXT_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                line[key] = value
        line.update(
            _extras(record)
        )  # caller-attached fields keep their (deterministic) insert order
        if record.exc_info:
            line["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            line["stack_info"] = self.formatStack(record.stack_info)
        return _mask_values(self._static, json.dumps(line, ensure_ascii=False, default=str))
