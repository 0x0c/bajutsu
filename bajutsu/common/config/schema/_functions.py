"""Read a config file into the schema, coercing the shapes YAML admits."""

from __future__ import annotations

from typing import Any


def _as_list(v: Any) -> Any:
    return [v] if isinstance(v, str) else v


def _check_platform(v: str | None) -> str | None:
    """Reject an unknown `platform` token at load time, so a typo fails loudly here.

    `None` means "derive the platform from the backend", so it passes through (BE-0009 Slice 4).
    """
    if v is None:
        return v
    # Imported lazily so this schema module carries no top-level dependency on `bajutsu.common.backends`
    # (only the sibling `resolve` module does); the token set is tiny and this validator runs once.
    from bajutsu.common.backends import PLATFORMS

    if v not in PLATFORMS:
        raise ValueError(f"invalid platform {v!r}: use one of {', '.join(PLATFORMS)}")
    return v
