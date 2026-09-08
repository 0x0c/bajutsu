"""Web backend (Playwright, Chromium — headless by default, headed on request).

Walks the DOM into normalized Elements and acts by coordinate-clicking the resolved
frame center — the same coordinate path the device backends take. The browser has a native semantic click
(`get_by_test_id().click()`), but using it would route matching through Playwright's
own engine and diverge from the determinism core; instead every action resolves through
the shared `base.resolve_unique` / `find_all` against a `query()` snapshot, so a scenario
behaves identically on web and iOS.

The id convention is `data-testid` (developer-set, non-localized) → `Selector.id`; ARIA
`role` (or the tag) → `traits`; accessible name / `aria-label` / text → `label`.

`playwright` is imported lazily (only when a browser is actually started), so importing
this module — or the default CLI path — never pulls in the heavy dependency.
"""

from ._functions import _device_context_kwargs as _device_context_kwargs
from ._functions import _playwright_error_types as _playwright_error_types
from ._functions import _rotate_point as _rotate_point
from ._functions import _start_browser as _start_browser
from ._functions import _wedge_guard as _wedge_guard
from ._functions import web_is_alive
from ._hit_result import _HitResult as _HitResult
from ._keyboard import _Keyboard as _Keyboard
from ._mouse import _Mouse as _Mouse
from ._page import _Page as _Page
from ._shared import Starter
from ._started import _Started as _Started
from .playwright_driver import _UNIT as _UNIT
from .playwright_driver import PlaywrightDriver

__all__ = ["PlaywrightDriver", "Starter", "web_is_alive"]
