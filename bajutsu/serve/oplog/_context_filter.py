"""Fill a record's correlation ids from the bound context, without clobbering explicit ones."""

from __future__ import annotations

import logging

from ._shared import _CONTEXT_KEYS


class _ContextFilter(logging.Filter):
    """Fill the correlation ids from the bound context, without clobbering explicit values.

    A caller can name an id directly (e.g. ``log_event(..., org=...)`` on the control plane, which
    binds nothing in context); the contextvar only fills the ids the caller left unset (the common
    case — the request / worker boundary bound them out-of-band).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        for key, var in _CONTEXT_KEYS:
            if getattr(record, key, None) is None:
                setattr(record, key, var.get())
        return True
