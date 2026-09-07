"""How a step addresses an element: the provided fields, combined with AND."""

from __future__ import annotations

from typing import TypedDict


class Selector(TypedDict, total=False):
    """How to address an element. Provided fields are combined with AND.

    The stable selector is `id` (non-localized, data-derived). `label` /
    `labelMatches` are auxiliary; `index` is a last resort (flaky).
    """

    # `id` / `idMatches` accept a single value or a list of candidates; a list matches an element
    # whose identifier equals (or glob-matches) *any* candidate — an OR (BE-0221). This lets one
    # shared scenario carry every platform's form of an id (`[stable.refresh, stable_refresh]`) so it
    # runs unchanged where the native id syntax differs (Android `android:id` can't hold `.`/`-`).
    # Ambiguity is unchanged: 2+ matching elements still fail fast in `resolve_unique`.
    id: str | list[str]  # exact accessibilityIdentifier (first choice)
    idMatches: str | list[str]  # glob pattern (assumes multiple matches, e.g. "*.submit")
    label: str  # exact accessibilityLabel (auxiliary / disambiguation only)
    labelMatches: str  # substring / regex over label
    traits: list[str]  # narrow by type (e.g. ["button"])
    value: str  # accessibility value match
    within: Selector  # scope to a parent (needs a hierarchical query; not implemented)
    index: int  # nth of multiple matches (last resort; flaky)
