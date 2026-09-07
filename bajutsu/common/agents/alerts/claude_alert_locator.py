"""The Claude-vision alert locator, behind the vendor-neutral AI backend (BE-0104)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bajutsu.common.agents.ai_config import AiConfig
from bajutsu.common.agents.claude_backed import ClaudeBackedAgent
from bajutsu.common.ai import (
    AiBackend,
    AnyTool,
    ImagePart,
    Message,
    MessageRequest,
    TextPart,
    ToolDef,
)
from bajutsu.common.analytics import usage
from bajutsu.common.evidence.redaction import Redactor
from bajutsu.common.screenshots import png_size

from ._functions import _decision_of

if TYPE_CHECKING:
    from .alert_decision import AlertDecision

# Sonnet over Opus: this fires mid-wait (BE-0269), so its round-trip latency is on the run's
# critical path — a locate-a-button task doesn't need Opus's extra reasoning depth.
LOCATOR_MODEL = "claude-sonnet-5"


# --- Claude vision locator (the production brain) ---

LOCATOR_SYSTEM = """You clear an unexpected iOS system prompt that is blocking an \
automated UI test. You are given a screenshot of the screen. A "system prompt" is an \
OS-level alert, action sheet, or dialog that is NOT part of the app under test — for \
example "Save Password?", a notification-permission alert, "Allow Paste", or a \
location-access request.

Call the tool `resolve_alert` exactly once:
- If no such prompt is present (the screenshot shows only the app), set present=false.
- If a prompt is present, set present=true and return x,y as the CENTER of the button \
to tap, in PIXEL coordinates of the screenshot. The image's exact pixel width and \
height are stated with the request: x runs from 0 at the left edge to width at the \
right, y from 0 at the top to height at the bottom. These phone screenshots are tall, \
so judge the vertical position carefully against the stated height.
- By default choose the dismissive, least-destructive button (e.g. "Not Now", \
"Don't Allow", "Cancel", "Close"). If an instruction is provided, follow it instead \
and tap the button it names."""

LOCATOR_TOOL: list[ToolDef] = [
    ToolDef(
        name="resolve_alert",
        description="Report whether a blocking system prompt is present and where to tap.",
        input_schema={
            "type": "object",
            "properties": {
                "present": {"type": "boolean"},
                "x": {"type": "number", "description": "button center x in pixels"},
                "y": {"type": "number", "description": "button center y in pixels"},
                "label": {"type": "string", "description": "the button's text"},
            },
            "required": ["present"],
        },
    )
]


class ClaudeAlertLocator(ClaudeBackedAgent):
    """AlertLocator backed by Claude vision, through the vendor-neutral backend (BE-0104)."""

    def __init__(
        self,
        backend: AiBackend | None = None,
        model: str | None = None,
        *,
        ai: AiConfig | None = None,
        redactor: Redactor | None = None,
    ) -> None:
        super().__init__(
            backend=backend, ai=ai, default_model=LOCATOR_MODEL, model=model, redactor=redactor
        )

    def locate(self, screenshot_png: bytes, instruction: str | None) -> AlertDecision:
        width, height = png_size(screenshot_png)
        text = (
            "Clear the blocking system prompt if one is present. "
            f"The screenshot is {width}x{height} pixels (width x height); give the "
            "button center as pixel coordinates within that range."
        )
        if instruction:
            # The instruction may be user-supplied (--alert-vision-instruction); mask secrets before it
            # reaches the model (BE-0047). The screenshot beside it cannot be pixel-masked.
            if self._redactor is not None:
                instruction = self._redactor.redact_text(instruction)
            text += f"\nInstruction for the prompt: {instruction}"
        response = self._ensure_backend().create_message(
            MessageRequest(
                system=LOCATOR_SYSTEM,
                messages=[
                    Message(
                        role="user",
                        content=[ImagePart(data=screenshot_png), TextPart(text=text)],
                    )
                ],
                tools=LOCATOR_TOOL,
                tool_choice=AnyTool(),
                model=self._model,
                max_tokens=512,
            )
        )
        self._record_usage(response, usage.CATEGORY_ALERT)
        return _decision_of(response, width, height)
