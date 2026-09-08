"""Evidence capture: instant and interval artifacts written during a run.

Instant artifacts (screenshot / elements) are written after each step; interval
artifacts (video / deviceLog / appTrace) are recorded for the whole scenario.
Instant captures land in run_dir/<step_id>/; interval captures run for the whole
scenario and land in run_dir/<scenario_id>/. Every artifact records its provider so
the manifest shows where it came from.
"""

from ._functions import _INTERVAL_FILE as _INTERVAL_FILE
from ._functions import _depicts as _depicts
from ._functions import _interval_filename as _interval_filename
from ._functions import _preferred_screenshot as _preferred_screenshot
from ._functions import (
    begin_after_screenshot,
    capture,
    reuse_screenshot,
    start_after_screenshot,
    step_view,
    write_elements,
    write_raw_tree,
    write_screenshot,
    write_wait_diagnostic,
)
from ._shared import _logger as _logger
from .artifact import Artifact
from .deferred_screenshot_sink import DeferredScreenshotSink
from .evidence_sink import EvidenceSink
from .file_sink import FileSink
from .null_sink import NullSink
from .step_view import StepView

__all__ = [
    "Artifact",
    "DeferredScreenshotSink",
    "EvidenceSink",
    "FileSink",
    "NullSink",
    "StepView",
    "begin_after_screenshot",
    "capture",
    "reuse_screenshot",
    "start_after_screenshot",
    "step_view",
    "write_elements",
    "write_raw_tree",
    "write_screenshot",
    "write_wait_diagnostic",
]
