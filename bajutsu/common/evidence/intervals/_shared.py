"""The capture commands and clock-correction bounds intervals are measured against."""

from __future__ import annotations

from collections.abc import Callable

from ._functions import start_device_log, start_video
from .interval import Interval

# Shared by every caller outside `bajutsu run` that needs an install+test-window recording bound:
# the on-device conformance/fault-injection suites' `tests/ondevice_evidence.py` and the codegen
# lane's `demos/showcase/android/screenrecord.py`. One definition and one rationale comment, so a
# future tuning change (the mp4s got too big, the window needs to grow) moves every caller together
# instead of leaving them to silently drift apart. 180 is a hard platform ceiling, not a default it
# clamps to: AOSP's screenrecord.cpp rejects any --time-limit above kMaxTimeLimitSec (180) with an
# error instead of capping it, so this cannot be raised. --size/--bit-rate keep the mp4 small enough
# for `/sdcard` and the artifact upload (screenrecord's own defaults are 20 Mbps at the AVD's full
# 1080x2400 panel).
SCREENRECORD_TIME_LIMIT_S = 180
SCREENRECORD_SIZE = "540x1200"
SCREENRECORD_BIT_RATE = 2_000_000


# kind -> starter, for the sink to dispatch on a capture token's kind
STARTERS: dict[str, Callable[..., Interval]] = {
    "video": start_video,
    "deviceLog": start_device_log,
}
INTERVAL_KINDS = frozenset({*STARTERS, "appTrace"})
