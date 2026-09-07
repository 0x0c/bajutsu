"""The Claude-vision tab locator, behind the vendor-neutral AI backend (BE-0104)."""

from __future__ import annotations

from bajutsu.common.agents.ai_config import AiConfig, language_instruction
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
from bajutsu.common.ai.prompts import NEVER_JUDGE_BOUNDARY
from bajutsu.common.screenshots import png_size

from ._functions import _targets_of
from .tab_target import TabTarget

TAB_LOCATOR_MODEL = "claude-opus-4-8"


# --- Claude vision locator (the production brain) ---

_SYSTEM = f"""You locate the tab bar of an iOS app for an automated crawl. You are given a \
screenshot of the screen. A "tab bar" is the row of top-level sections — usually along the \
bottom edge — that switches the whole view (e.g. Home / Search / Profile). It is NOT a navigation \
bar, a toolbar, or in-content buttons.

Call the tool `find_tabs` exactly once:
- If there is no tab bar on this screen, return an empty `tabs` array.
- Otherwise return one entry per tab, left to right, each with x,y as the CENTER of the tab in \
PIXEL coordinates of the screenshot. The image's exact pixel width and height are stated with the \
request: x runs from 0 at the left edge to width at the right, y from 0 at the top to height at \
the bottom. These phone screenshots are tall, so judge the vertical position carefully against the \
stated height — a bottom tab bar sits near the bottom. Include the tab's visible text in `label` \
when it has one.
- You only report where the tabs are. {NEVER_JUDGE_BOUNDARY}"""

_FIND_TABS_TOOL: list[ToolDef] = [
    ToolDef(
        name="find_tabs",
        description="Report the app's tab bar items (empty when there is no tab bar).",
        input_schema={
            "type": "object",
            "properties": {
                "tabs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number", "description": "tab center x in pixels"},
                            "y": {"type": "number", "description": "tab center y in pixels"},
                            "label": {"type": "string", "description": "the tab's visible text"},
                        },
                        "required": ["x", "y"],
                    },
                }
            },
            "required": ["tabs"],
        },
    )
]


class ClaudeTabLocator(ClaudeBackedAgent):
    """TabLocator backed by Claude vision, through the vendor-neutral backend (BE-0104)."""

    def __init__(
        self,
        backend: AiBackend | None = None,
        model: str | None = None,
        *,
        ai: AiConfig | None = None,
    ) -> None:
        super().__init__(backend=backend, ai=ai, default_model=TAB_LOCATOR_MODEL, model=model)
        self._lang = language_instruction(ai)  # output-language suffix, empty for `auto` (BE-0188)

    def locate(self, screenshot_png: bytes) -> list[TabTarget]:
        width, height = png_size(screenshot_png)
        text = (
            f"Find the tab bar. The screenshot is {width}x{height} pixels (width x height); give "
            "each tab center as pixel coordinates within that range."
        )
        response = self._ensure_backend().create_message(
            MessageRequest(
                system=_SYSTEM + self._lang,
                messages=[
                    Message(
                        role="user",
                        content=[ImagePart(data=screenshot_png), TextPart(text=text)],
                    )
                ],
                tools=_FIND_TABS_TOOL,
                tool_choice=AnyTool(),
                model=self._model,
                max_tokens=512,
            )
        )
        # reporting only (BE-0104) — never on the pass/fail path
        self._record_usage(response)
        return _targets_of(response, width, height)
