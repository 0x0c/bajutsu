"""The poll intervals and failure vocabulary the step loop is written against."""

from __future__ import annotations

import logging
from collections.abc import Callable

from bajutsu.common.drivers import base
from bajutsu.common.scenario import Step

_logger = logging.getLogger(__name__)


# A recursive step runner: run these steps against this active driver, return the failure or None.
# The driver is passed explicitly so a web block can hand its inner steps a WebView driver without
# any shared mutable state (BE-0172).
_ExecSteps = Callable[[list[Step], base.Driver], str | None]
