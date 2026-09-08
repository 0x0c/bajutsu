"""Turn a requirement into the one-line remedy a user can act on."""

from __future__ import annotations

from ._shared import InstallMethod
from .brew import Brew
from .extra import Extra
from .manual import Manual
from .playwright import Playwright
from .tool import Tool


def remedy(method: InstallMethod) -> str:
    """The one-line remedy for an install method — the command to run, or a manual hint verbatim."""
    match method:
        case Extra(name):
            return f"`uv sync --extra {name}`"
        case Brew(formula):
            return f"`brew install {formula}`"
        case Playwright(browser):
            return f"`uv run playwright install {browser}`"
        case Manual(hint):
            return hint
    # The match is exhaustive over InstallMethod; this explicit terminal keeps every path
    # returning or raising (CodeQL flags a bare implicit fall-through) and guards a future variant.
    raise AssertionError(f"unhandled InstallMethod: {method!r}")  # pragma: no cover


def playwright_browser(engine: str) -> Tool:
    """The browser tool for a Playwright engine, built on demand rather than baked in.

    The engine is chosen per run, so it is not a static entry in the web backend's tool list — a
    `firefox` run needs `firefox`, not `chromium`.
    """
    return Tool(engine, Playwright(engine))
