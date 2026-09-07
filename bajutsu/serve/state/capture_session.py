"""The live state of an active capture session (BE-0012)."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from bajutsu.common.drivers import base as driver_base
from bajutsu.common.evidence.redaction import Redactor
from bajutsu.common.scenario.models import Step


@dataclass
class CaptureSession:
    """Live state for an active capture session (BE-0012).

    Holds the in-process Driver across mark requests — the one architectural departure from
    the stateless shell-out pattern. A single-session guard prevents two concurrent captures
    on the same state.
    """

    driver: driver_base.Driver
    target: str
    elements: list[driver_base.Element]
    screen_size: tuple[float, float]
    namespaces: list[str]
    redactor: Redactor | None
    actor: str | None = None
    # The login session that started the capture (BE-0393 unit 2). The capture drives the config
    # *that* session is bound to, so the authored scenario has to be saved into the same one — and
    # holding the id rather than re-reading it at finish also freezes the destination against a
    # rebind partway through, the same reason a job freezes its working directory at enqueue.
    login_session: str | None = None
    steps: list[Step] = field(default_factory=list)
    screenshot_path: Path = field(default_factory=lambda: Path(os.devnull))
    prev_fingerprint: str = ""
    # Releases whatever backs `driver` when the session ends — for XCUITest the `xcodebuild` runner
    # subprocess, which dropping the session would otherwise leak (BE-0290). Default is a no-op so a
    # session built without one (older callers, tests) is still safe to close.
    teardown: Callable[[], None] = field(default=lambda: None)
