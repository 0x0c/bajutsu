"""The transport seam and timeouts the live route speaks WebDriver over."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

# (method, path, json body) -> (HTTP status, decoded JSON). Injectable so the wire mapping is tested
# against a fake; the default talks HTTP(S) to the grid's WebDriver endpoint.
WdTransportFn = Callable[[str, str, Mapping[str, Any] | None], tuple[int, Any]]
