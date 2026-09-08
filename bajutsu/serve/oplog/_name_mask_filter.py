"""Mask structured fields by name, so a token never reaches a log line."""

from __future__ import annotations

import logging

from bajutsu.common.evidence.redaction import PLACEHOLDER


class _NameMaskFilter(logging.Filter):
    """Mask sensitive structured fields by *name* (`authorization`, `token`, …) to ``[REDACTED]``.

    Runs as a handler filter so it covers every record this handler writes, including ones
    propagated from child loggers. Value-based masking happens later, on the fully rendered line
    (`_mask_values`), so a secret carried by a non-string field is caught there too.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Imported in the method, not at module load: `_functions` installs this filter, and rule 5
        # breaks the cycle the split creates on this side.
        from ._functions import _extras, _is_sensitive_key

        for key in _extras(record):
            if _is_sensitive_key(key):
                setattr(record, key, PLACEHOLDER)
        return True
