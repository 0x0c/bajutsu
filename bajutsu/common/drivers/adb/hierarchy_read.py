"""One resident-channel read: the hierarchy XML and its read mark (BE-0332)."""

from __future__ import annotations

from dataclasses import dataclass, field


# A resident UI Automator server (BE-0245) returns the hierarchy over an already-open channel,
# skipping the ~2.4 s per-invocation `uiautomator dump` startup. Its response is UI Automator's own
# XML, unchanged, so `parse_hierarchy` consumes it identically — only the transport differs.
@dataclass(frozen=True)
class HierarchyRead:
    """One resident-channel read: the hierarchy XML and its read mark (BE-0332 Unit 3).

    `mark` is the device-clock timestamp (`SystemClock.uptimeMillis`) of the most recent accessibility
    event the resident reader had observed when it served this dump. `AdbDriver` trusts a read once its
    `mark` postdates the mark it took before actuating, so a stable-but-stale tree — one that agrees
    with itself yet predates the last gesture — is no longer accepted (the read-lag defect). It is None
    on the `uiautomator dump` fallback, which carries no such stamp; there the wall-clock budget stands
    in, exactly as before this unit.

    `raw` is the body exactly as the resident server answered it, before `narrow_to_active_window`
    strips SystemUI decor windows — `text` is what that narrowing produced. None when the caller applies
    no such transform, so a `rawTree` capture (`RawSourceProvider`) has both halves to diff a mismatch
    against: the device's own dump, and bajutsu's own processing of it.

    `native_z` maps each opted-in view's content key to its own `View.getZ()` (BE-0355 Unit 3), keyed
    the way it is because the device measures those values in a second walk whose node sequence does
    not line up with the dumped body's. Empty on the dump fallback, on a server that does not report
    it, and on an app that opted no view in.
    """

    text: str
    mark: float | None = None
    raw: str | None = None
    native_z: dict[str, float] = field(default_factory=dict)
