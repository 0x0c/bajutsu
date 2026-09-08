"""Convention score for an app — how ready it is to be tested, plus the screen probe that feeds it.

Pure scoring computed from a screen (a list of Element): id coverage over
actionable elements, namespace conformance, and id uniqueness. AI is not
involved. The screen probe (`probe_screen`) that reads that screen from the device is
shared by the CLI and serve doctors (BE-0199); the environment/connection *gates* that decide
whether to probe stay with each caller (they need a device and their own UX).
"""

from ._functions import (
    ACTIONABLE_TRAITS,
    FAIL_COVERAGE,
    OK_COVERAGE,
    namespace_of,
    probe_screen,
    render,
    score,
)
from ._functions import _first_udid as _first_udid
from ._functions import _is_actionable as _is_actionable
from .doctor_probe_error import DoctorProbeError
from .score import Score

__all__ = [
    "ACTIONABLE_TRAITS",
    "FAIL_COVERAGE",
    "OK_COVERAGE",
    "DoctorProbeError",
    "Score",
    "namespace_of",
    "probe_screen",
    "render",
    "score",
]
