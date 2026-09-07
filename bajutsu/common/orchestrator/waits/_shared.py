"""The poll intervals and debounce counts every condition wait is measured in."""

from __future__ import annotations

import logging
from collections.abc import Callable

_logger = logging.getLogger(__name__)

# Emits a run-log line while a wait is pending; the float is the seconds left before timeout. Bound
# by the caller (the run loop) to prefix the scenario/step and format the condition.
WaitTick = Callable[[float], None]
