"""Deterministic network stubs.

A mock matches an outgoing request (reusing the request-side fields of the traffic matcher) and
returns a canned response instead of hitting the network.
"""

from .mock import Mock
from .mock_response import MockResponse

__all__ = ["Mock", "MockResponse"]
