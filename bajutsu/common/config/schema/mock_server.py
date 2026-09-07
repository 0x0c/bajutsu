"""The mock server stubbing what the app under test calls, as written under `mockServer:`."""

from __future__ import annotations

from ._model import _Model


class MockServer(_Model):
    """A mock server that stubs the dependencies the app under test *calls* (`mockServer:` config)."""

    cmd: str
    port: int
    stubs: str | None = None
