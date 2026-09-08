"""The error raised when a streamed upload crosses its byte cap mid-transfer."""

from __future__ import annotations


class UploadTooLarge(Exception):
    """The streamed upload crossed its byte cap mid-transfer — distinct from a rejected
    ``Content-Length`` header, since a lying or chunked-without-length request can't be caught
    before reading."""
