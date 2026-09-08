"""ClaudeAgent — the authoring agent backed by Claude (Anthropic SDK).

Implements the Agent protocol: given an Observation, the model is forced to call
one tool to either propose the next UI action (tap/type/wait) or finish (with the
assertions that verify the goal). The system prompt and tool definitions are static
and prompt-cached; the per-turn observation is the variable user message.

`anthropic` is lazy-imported so this module loads without an API key, and the
client is injectable for testing.
"""

from ._assertion_args import _AssertionArgs as _AssertionArgs
from ._functions import _LARGE_SCREEN_ELEMENTS as _LARGE_SCREEN_ELEMENTS
from ._functions import _combine as _combine
from ._functions import _has_target as _has_target
from ._functions import _hist_hint as _hist_hint
from ._functions import _history_line as _history_line
from ._functions import _provenance as _provenance
from ._functions import _render as _render
from ._functions import _target as _target
from ._functions import _to_assertion as _to_assertion
from ._functions import _to_proposal as _to_proposal
from ._functions import _user_content as _user_content
from ._functions import proposal_from_call, steps_from_plan
from ._shared import _PLAN_PROP as _PLAN_PROP
from ._shared import _REASON_PROP as _REASON_PROP
from ._shared import _TARGET_PROPS as _TARGET_PROPS
from ._target_args import _TargetArgs as _TargetArgs
from ._tool_args import _ToolArgs as _ToolArgs
from .claude_agent import (
    MODEL,
    PLAN_SYSTEM,
    PLAN_TIMEOUT_S,
    PLAN_TOOL,
    SYSTEM_PROMPT,
    TOOLS,
    ClaudeAgent,
)

__all__ = [
    "MODEL",
    "PLAN_SYSTEM",
    "PLAN_TIMEOUT_S",
    "PLAN_TOOL",
    "SYSTEM_PROMPT",
    "TOOLS",
    "ClaudeAgent",
    "proposal_from_call",
    "steps_from_plan",
]
