"""What a driver actually did to the screen — the record behind the `actionLog` evidence kind.

A step's outcome has always named its action and its duration, never the concrete gesture: which
coordinate a tap injected, which two endpoints a swipe travelled, which channel carried it. Those
values exist only inside a driver, for the moment between resolving them and sending them, so the
driver is the only layer that can record them.

Three rules shape the record, and every backend honors them:

1. It holds the coordinate that was really handed to the platform, and never one reconstructed
   afterwards. A driver that computes a frame center and sends it records that center; a handle-based
   iOS tap leaves `points` empty, because XCUITest picked the point on the far side of the handle and
   writing the frame's center here would present a guess as a measurement.
2. It costs no device work. Every value is one the actuator already had for its own use, so recording
   adds no query, no read, and no round trip.
3. It carries no string a scenario authored, because `manifest.json` is written without a redactor: a
   `type` step's text, a `selectOption`'s option, and an element's accessibility label can each hold a
   resolved `${secrets.*}`. `target` is therefore always the resolved `Element["identifier"]`, and a
   typed string leaves not even its length behind (`evidence/redaction.py` replaces a secret with a
   fixed-width placeholder precisely so no artifact discloses one's length).

The record is evidence only. Nothing on the verdict path reads it — no assertion, wait, or extract —
so it cannot influence pass/fail (prime directive 1).
"""

from ._shared import CHANNELS, GESTURES, SUBSTITUTIONS, UNITS
from .actuation import Actuation
from .actuation_log import MAX_RECORDS, ActuationLog
from .actuation_reporter import ActuationReporter
from .drained import Drained

__all__ = [
    "CHANNELS",
    "GESTURES",
    "MAX_RECORDS",
    "SUBSTITUTIONS",
    "UNITS",
    "Actuation",
    "ActuationLog",
    "ActuationReporter",
    "Drained",
]
