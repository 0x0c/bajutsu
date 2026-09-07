"""WebView bridge client — Python side of the BajutsuKit WebView channel.

Sends HTTP requests to the BajutsuKit bridge server running inside the app under test.
The server exposes the WebView's DOM as normalized elements and dispatches tap actions.
"""

from .dom_source import DomSource
from .web_context_driver import _UNIT as _UNIT
from .web_context_driver import WebContextDriver
from .web_view_bridge import WebViewBridge

__all__ = ["DomSource", "WebContextDriver", "WebViewBridge"]
