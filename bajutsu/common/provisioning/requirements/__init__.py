"""The single declarative source of truth for what each backend/capability needs (BE-0164).

One mapping of backend family (`xcuitest` / `adb` / `playwright` / `fake`) and optional
capability (`ai` / `visual` / `mcp`) to: the pip extra to sync and the external tools to have on
PATH, each with how to install it when missing (a Homebrew formula, a `playwright install
<browser>`, a pip extra, or a manual-only hint). ``preflight``'s remedy strings and the
config-aware installer (``provision``) both read from here, so the same fact is never hardcoded
in two places that can drift.

Pure data plus a pure ``remedy`` renderer — no subprocess and no config — so it stays in the
deterministic core and is trivially testable. A new backend plugs its requirements in here rather
than forking the installer or the preflight (prime directive #3).
"""

from ._functions import playwright_browser, remedy
from ._shared import BACKENDS, CAPABILITIES, InstallMethod
from .brew import Brew
from .extra import Extra
from .manual import Manual
from .playwright import Playwright
from .requirement import Requirement
from .tool import Tool

__all__ = [
    "BACKENDS",
    "CAPABILITIES",
    "Brew",
    "Extra",
    "InstallMethod",
    "Manual",
    "Playwright",
    "Requirement",
    "Tool",
    "playwright_browser",
    "remedy",
]
