"""The seam every model provider sits behind, so no caller names a vendor (BE-0104)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .message_request import MessageRequest
    from .message_response import MessageResponse


class AiBackend(Protocol):
    """A model provider behind one interface (BE-0104).

    An adapter implements this to translate a `MessageRequest` into a concrete provider's API and
    the provider's reply back into a `MessageResponse`. The only method the AI paths need is a
    single forced-tool turn.
    """

    def create_message(self, request: MessageRequest) -> MessageResponse: ...
