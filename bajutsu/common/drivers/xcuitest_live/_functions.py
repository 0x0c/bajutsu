"""Drive one WebDriver session: build requests, read replies, and time each call out."""

from __future__ import annotations

import http.client
import json
import urllib.parse
from collections.abc import Mapping
from typing import Any

from ._shared import WdTransportFn
from .web_driver_error import WebDriverError

# Per-request socket timeouts, split by idempotency the way the runner channel splits them: a read is
# tight, a write (a synthesized UI event) gets more headroom on a contended grid. Unlike the runner
# channel the live client does not retry — a WebDriver click cannot be re-issued safely after delivery
# — so each request simply fails loudly on timeout rather than hanging.
_READ_TIMEOUT_SECONDS = 15
_WRITE_TIMEOUT_SECONDS = 30


def _timeout_for(method: str) -> float:
    return _READ_TIMEOUT_SECONDS if method == "GET" else _WRITE_TIMEOUT_SECONDS


def _raw_wd_transport(endpoint: str) -> WdTransportFn:
    """One HTTP(S) attempt to a WebDriver endpoint, decoding the JSON reply.

    The endpoint may carry a base path (e.g. `.../wd/hub`); it is prefixed to every request path so a
    relative `/session` resolves against it.
    """
    parsed = urllib.parse.urlparse(endpoint)
    base_path = parsed.path.rstrip("/")
    host = parsed.hostname or ""
    https = parsed.scheme == "https"
    port = parsed.port or (443 if https else 80)

    def transport(method: str, path: str, body: Mapping[str, Any] | None) -> tuple[int, Any]:
        conn_cls = http.client.HTTPSConnection if https else http.client.HTTPConnection
        conn = conn_cls(host, port, timeout=_timeout_for(method))
        try:  # pragma: no cover - exercised against a real grid, not on the gate
            payload = json.dumps(body).encode() if body is not None else None
            headers = {"Content-Type": "application/json"} if payload is not None else {}
            conn.request(method, base_path + path, body=payload, headers=headers)
            resp = conn.getresponse()
            raw = resp.read()
            data = json.loads(raw) if raw else {}
        except (
            OSError,
            http.client.HTTPException,
            json.JSONDecodeError,
        ) as exc:  # pragma: no cover - see above
            raise WebDriverError(f"WebDriver {method} {path} failed: {exc}") from exc
        else:
            return resp.status, data
        finally:
            conn.close()

    return transport


def _norm_type(type_: str) -> str:
    """Normalize an XCUITest element type (`XCUIElementTypeButton`) to a common trait (`button`)."""
    t = type_.removeprefix("XCUIElementType")
    return t[:1].lower() + t[1:] if t else t


def _str_or_none(value: Any) -> str | None:
    return None if value is None or value == "" else str(value)


def _is_true(value: Any) -> bool:
    """Whether a WebDriver attribute that Appium returns as a `"true"` / `"false"` string is true."""
    return str(value).lower() == "true"
