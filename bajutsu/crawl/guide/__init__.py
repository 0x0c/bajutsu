"""AI guide for the autonomous crawl (BE-0038).

The guide proposes which replayable actions to try from a screen — taps and *realistic* text
inputs that may open a new screen or enable a disabled control whose precondition isn't obvious
(a valid email, a password that meets the rules). It only influences **what to explore**: screen
identity, transition/crash detection and the screen map stay deterministic in
[`core.py`](core.py), so the crawl is never a verdict (prime directive #1).

The model call sits behind an ``ActionProposer`` protocol, so the guide is exercised in the gate
with a scripted fake — no LLM, mirroring how `record` tests the authoring agent. The proposer's
actions are unioned with the deterministic `candidate_actions` as a safety net, so the crawl
still advances if the model proposes nothing useful.
"""

from ._functions import Report, ai_guide, make_guide
from ._functions import _actions_from as _actions_from
from ._functions import _content as _content
from ._functions import _dedup as _dedup
from ._functions import _locate_tabs as _locate_tabs
from ._functions import _proposal_from as _proposal_from
from ._functions import _render_elements as _render_elements
from ._functions import _secure_fields as _secure_fields
from ._functions import _text_block as _text_block
from ._secure_fields import _SecureFields as _SecureFields
from .action_proposer import ActionProposer
from .claude_action_proposer import _PROPOSE_TOOL as _PROPOSE_TOOL
from .claude_action_proposer import _SYSTEM as _SYSTEM
from .claude_action_proposer import MODEL, ClaudeActionProposer
from .proposal import Proposal

__all__ = [
    "MODEL",
    "ActionProposer",
    "ClaudeActionProposer",
    "Proposal",
    "Report",
    "ai_guide",
    "make_guide",
]
