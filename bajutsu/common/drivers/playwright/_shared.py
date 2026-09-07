"""The browser starter seam and the memoized Playwright error types the driver catches."""

from __future__ import annotations

from collections.abc import Callable

from ._started import _Started

Starter = Callable[[bool], _Started]
