"""A minimal in-house W3C WebDriver client over an injectable transport (BE-0238)."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from typing import Any

from ._shared import WdTransportFn
from .web_driver_error import WebDriverError

# The W3C element-reference key: `findElements` returns each element as `{ELEMENT_KEY: "<id>"}`, and
# every per-element request addresses it by that opaque id — the live counterpart of the runner's
# opaque handle.
ELEMENT_KEY = "element-6066-11e4-a52e-4f735466cecf"


class WebDriverClient:
    """A minimal in-house W3C WebDriver client over an injectable transport (BE-0238)."""

    def __init__(self, transport: WdTransportFn) -> None:
        self._transport = transport
        self._session: str | None = None

    def _value(self, method: str, path: str, body: Mapping[str, Any] | None) -> Any:
        """Send one request and return the WebDriver `value`, raising loudly on any error reply.

        Every W3C reply wraps its result in a `value`; a non-2xx status or a missing envelope is an
        endpoint failure, surfaced as `WebDriverError` rather than mistaken for a test outcome.
        """
        status, data = self._transport(method, path, body)
        if not isinstance(data, Mapping) or "value" not in data:
            raise WebDriverError(f"{method} {path}: malformed reply (status={status}): {data!r}")
        if status >= 400:
            raise WebDriverError(f"{method} {path} failed (status={status}): {data['value']!r}")
        return data["value"]

    def _session_path(self, suffix: str) -> str:
        if self._session is None:
            raise WebDriverError("no open WebDriver session")
        return f"/session/{self._session}{suffix}"

    def new_session(self, capabilities: Mapping[str, Any]) -> str:
        """Open a session with *capabilities* (W3C `alwaysMatch`) and return its id."""
        value = self._value(
            "POST", "/session", {"capabilities": {"alwaysMatch": dict(capabilities)}}
        )
        session = value.get("sessionId") if isinstance(value, Mapping) else None
        if not session:
            raise WebDriverError(f"new session returned no sessionId: {value!r}")
        self._session = str(session)
        return self._session

    def delete_session(self) -> None:
        """Close the open session (a no-op when none is open, so teardown is idempotent)."""
        if self._session is None:
            return
        self._transport("DELETE", f"/session/{self._session}", None)
        self._session = None

    def find_elements(self, using: str, value: str) -> list[str]:
        """Return the element ids matching a locator (empty when none match)."""
        found = self._value(
            "POST", self._session_path("/elements"), {"using": using, "value": value}
        )
        if not isinstance(found, list):
            raise WebDriverError(f"elements was not a list: {found!r}")
        ids: list[str] = []
        for item in found:
            if not isinstance(item, Mapping) or ELEMENT_KEY not in item:
                raise WebDriverError(f"element reply missing {ELEMENT_KEY!r}: {item!r}")
            ids.append(item[ELEMENT_KEY])
        return ids

    def attribute(self, element_id: str, name: str) -> Any:
        """Return one element attribute (`name` / `label` / `value` / `type` / `enabled` / …)."""
        return self._value(
            "GET", self._session_path(f"/element/{element_id}/attribute/{name}"), None
        )

    def rect(self, element_id: str) -> Mapping[str, Any]:
        """Return an element's bounding rect (`x` / `y` / `width` / `height`)."""
        value = self._value("GET", self._session_path(f"/element/{element_id}/rect"), None)
        if not isinstance(value, Mapping):
            raise WebDriverError(f"rect was not a mapping: {value!r}")
        return value

    def window_rect(self) -> Mapping[str, Any]:
        """Return the window rect (`x` / `y` / `width` / `height`) — the device screen on iOS."""
        value = self._value("GET", self._session_path("/window/rect"), None)
        if not isinstance(value, Mapping):
            raise WebDriverError(f"window rect was not a mapping: {value!r}")
        return value

    def click(self, element_id: str) -> None:
        """Tap the element addressed by *element_id*."""
        self._value("POST", self._session_path(f"/element/{element_id}/click"), {})

    def screenshot(self) -> bytes:
        """Return the current screen as PNG bytes (the endpoint returns them base64-encoded)."""
        encoded = self._value("GET", self._session_path("/screenshot"), None)
        try:
            return base64.b64decode(encoded)
        except (binascii.Error, TypeError) as exc:
            raise WebDriverError(f"screenshot was not valid base64: {encoded!r}") from exc

    def is_ready(self) -> bool:
        """Whether the endpoint reports itself ready to serve (`GET /status`)."""
        value = self._value("GET", "/status", None)
        return bool(value.get("ready")) if isinstance(value, Mapping) else False

    def execute(self, script: str, args: list[Any]) -> Any:
        """Run an Appium `mobile:` command (`POST /execute/sync`) and return its result.

        The live route's gestures are Appium's XCUITest `mobile:` commands — the native counterparts of
        the local runner's semantic endpoints — driven through the standard W3C execute-script channel.
        """
        return self._value(
            "POST", self._session_path("/execute/sync"), {"script": script, "args": args}
        )

    def active_element(self) -> str:
        """Return the focused element's id (`GET /element/active`), for text entry."""
        value = self._value("GET", self._session_path("/element/active"), None)
        if not isinstance(value, Mapping) or ELEMENT_KEY not in value:
            raise WebDriverError(f"active element reply missing {ELEMENT_KEY!r}: {value!r}")
        return str(value[ELEMENT_KEY])

    def send_keys(self, element_id: str, text: str) -> None:
        """Type *text* into the element addressed by *element_id* (`POST /element/{id}/value`)."""
        self._value("POST", self._session_path(f"/element/{element_id}/value"), {"text": text})
