"""ClaudeTriageAgent — a Claude-backed diagnosis behind the TriageAgent protocol.

Same boundary as the rule-based `HeuristicTriageAgent`: triage is **advisory**. Given a
`TriageContext` (the failure, the failed step, the a11y element tree nearest the failure, and
the scenario definition), the model is forced to call one tool that returns a structured
`Triage` (summary + category + minimal suggestions). It reasons over the same evidence the
heuristic sees, just without hand-written rules.

`anthropic` is lazy-imported so this module loads without an API key, and the client is
injectable for testing — mirroring `claude_agent.ClaudeAgent`.
"""

from ._functions import _CATEGORIES as _CATEGORIES
from ._functions import NO_DIAGNOSIS_SUMMARY
from ._functions import _cross_run_user_content as _cross_run_user_content
from ._functions import _forced_diagnose as _forced_diagnose
from ._functions import _parse_fix as _parse_fix
from ._functions import _render as _render
from ._functions import _render_cross_run as _render_cross_run
from ._functions import _render_evidence as _render_evidence
from ._functions import _representative_screenshot_run as _representative_screenshot_run
from ._functions import _to_triage as _to_triage
from ._functions import _user_content as _user_content
from ._shared import MODEL
from .claude_cross_run_triage_agent import _CROSS_RUN_CATEGORIES as _CROSS_RUN_CATEGORIES
from .claude_cross_run_triage_agent import (
    CROSS_RUN_SYSTEM_PROMPT,
    CROSS_RUN_TOOLS,
    ClaudeCrossRunTriageAgent,
)
from .claude_triage_agent import SYSTEM_PROMPT, TOOLS, ClaudeTriageAgent

__all__ = [
    "CROSS_RUN_SYSTEM_PROMPT",
    "CROSS_RUN_TOOLS",
    "MODEL",
    "NO_DIAGNOSIS_SUMMARY",
    "SYSTEM_PROMPT",
    "TOOLS",
    "ClaudeCrossRunTriageAgent",
    "ClaudeTriageAgent",
]
