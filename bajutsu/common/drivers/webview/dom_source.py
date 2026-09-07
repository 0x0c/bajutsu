"""The bridge seam the WebView driver reads through, satisfied by the client and by fakes."""

from __future__ import annotations

from typing import Protocol

from bajutsu.common.drivers.base import Element, Point


class DomSource(Protocol):
    """Minimal bridge interface — satisfied by WebViewBridge and test fakes."""

    def query_dom(self, webview_id: str) -> list[Element]: ...
    def tap_element(self, webview_id: str, point: Point) -> None: ...
    def type_text(self, webview_id: str, text: str) -> None: ...
    def scroll_to(self, webview_id: str, element_id: str) -> None: ...
