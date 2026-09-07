"""One on-screen element, normalized from whatever shape a backend reports."""

from __future__ import annotations

from typing import TypedDict

from ._shared import Frame


class Element(TypedDict):
    """A single on-screen element, normalized from a device backend's output."""

    identifier: str | None
    label: str | None
    traits: list[str]
    value: str | None
    frame: Frame
    # The element's real front-to-back position, measured by the app itself through the opt-in
    # app-side hook (BE-0355) — never derived from this list's own document order, which is only the
    # paint-order proxy `topmost_at_point` below already warns about. Diagnostic only: no selector
    # matches on it and no occlusion check reads it, so `is_tappable` / `topmost_at_point` /
    # XCUITest's `isHittable` are unaffected. `None` is an honest absence — a backend with no such
    # hook, or an app that has not opted in — rather than a wrong guess. UIKit screens (through
    # BajutsuKit's responder) and Android `View` screens in an opted-in app report a value; every
    # other backend, and every app that has not opted in, reports `None` (BE-0355).
    # `_collapse_identical_duplicates`'s content key deliberately omits it: two candidates that
    # agree on every other reported field still collapse, however far apart they measure.
    nativeZ: float | None
