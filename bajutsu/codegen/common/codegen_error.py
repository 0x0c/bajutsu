"""The error raised for a codegen request no target can fulfil."""

from __future__ import annotations


class CodegenError(ValueError):
    """A codegen request that cannot be fulfilled.

    Raised at generation time (never a silent stub): an unknown emit, an emit on the wrong target
    (Playwright needs a web target, UI Automator an Android target), or a scenario construct no
    target can translate faithfully (`if` / `forEach` control flow or an `extract` capture, BE-0297).
    Both transports — the `codegen` CLI and the serve `/api/codegen` endpoint — translate it into
    their own error surface.
    """
