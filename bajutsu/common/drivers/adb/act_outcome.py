"""What the device did with one actuation request, and whether the tree has caught up."""

from __future__ import annotations

from dataclasses import dataclass

from .hierarchy_read import HierarchyRead


@dataclass(frozen=True)
class ActOutcome:
    """What the device did with one `ActRequest`, and whether the tree has caught up with it.

    `published_mark` is the whole reason this is not a bare bool. The device answers it from the
    accessibility event stream it is already observing — the one place the question "has this gesture
    reached the tree yet?" can be answered directly, rather than inferred by re-reading trees a round
    trip away. When it is set, the read that follows this gesture cannot describe the pre-gesture
    screen, so the driver arms no read-lag barrier for it (BE-0339 Unit 5).

    None is the honest answer for every case the device could not confirm — a gesture that published
    nothing because it moved no frame, one whose publish outran the endpoint's budget, and a server
    old enough not to report at all — and it restores the barrier exactly as it stood before.
    """

    acted: bool  # False is the `stale` reply: the identity no longer names the same nodes there
    published_mark: float | None  # the device-clock time of an event postdating the injection
    # The tree the device dumped after that publish, when it confirmed one (BE-0407 unit 19). Carried
    # only alongside a confirmation, because that confirmation is exactly what makes it safe: an
    # event postdates the injection, so this dump cannot describe the pre-gesture screen. None
    # None otherwise: an unconfirmed gesture, an older server, and a target that asked for `nativeZ`
    # (whose reading this reply cannot carry, so the driver reads for itself rather than report every
    # element's position as absent).
    read: HierarchyRead | None = None
