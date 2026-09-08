"""Normalized request / response types and the `AiBackend` protocol (BE-0104).

The seam describes *only* what Bajutsu's AI paths actually ask of a model, and nothing more (the
BE-0104 capability audit): one forced-tool `create_message` turn carrying a system prompt, a user
message of text and/or images, and tool definitions; a response of text and tool-use content
blocks. No streaming and no multi-turn `tool_result` feedback — no current path uses them (the
`record` loop drives many single-shot turns, not one turn with tool results fed back).

These types are Bajutsu's own, deliberately *not* re-exports of any vendor SDK, so no call site
depends on a provider's message / tool / image shape. An adapter (see `bajutsu.common.ai.anthropic`)
translates them to and from a concrete provider.
"""

from .ai_backend import AiBackend
from .any_tool import AnyTool
from .image_part import ImagePart
from .message import ContentPart, Message
from .message_request import MessageRequest, ToolChoice
from .message_response import ContentBlock, MessageResponse
from .named_tool import NamedTool
from .text_block import TextBlock
from .text_part import TextPart
from .tool_def import ToolDef
from .tool_use_block import ToolUseBlock

__all__ = [
    "AiBackend",
    "AnyTool",
    "ContentBlock",
    "ContentPart",
    "ImagePart",
    "Message",
    "MessageRequest",
    "MessageResponse",
    "NamedTool",
    "TextBlock",
    "TextPart",
    "ToolChoice",
    "ToolDef",
    "ToolUseBlock",
]
