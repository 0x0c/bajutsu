"""Vision tab locator — find a tab bar's items the accessibility tree can't address (BE-0038).

A tab bar is usually exposed in the tree as a `tab`-trait button with an identifier, and the
crawl taps those directly (`candidate_actions` orders them tabs-first). But some apps build a
custom tab bar from images with no identifier and no `tab` trait, so the accessibility tree can't address
the individual tabs — the same blind spot the system-alert guard ([`alerts.py`](alerts.py))
works around. When the tree exposes no tabs, this locator takes a screenshot, asks Claude vision
for the tab bar items, and returns each as a normalized [0,1] coordinate the crawl turns into a
replayable coordinate tap (`Action(kind="tap_point")`).

Like the alert guard it only decides *where to tap* — the guide layer's "what to try". Screen
identity, transitions and crashes stay deterministic in [`core.py`](core.py), and the tap is
replayed by its stored coordinate (never re-located), so the crawl is never a verdict
(prime directive #1). The locator is injectable: production uses Claude vision; tests inject a
deterministic fake, mirroring how the alert guard and the action proposer are tested.
"""

from ._functions import _TAB_BAR_LABEL as _TAB_BAR_LABEL
from ._functions import _is_tab as _is_tab
from ._functions import _targets_of as _targets_of
from ._functions import _uikit_addressable_tabs as _uikit_addressable_tabs
from ._functions import addressable_tabs, needs_vision_tabs, tab_bar_present
from .claude_tab_locator import _FIND_TABS_TOOL as _FIND_TABS_TOOL
from .claude_tab_locator import _SYSTEM as _SYSTEM
from .claude_tab_locator import TAB_LOCATOR_MODEL, ClaudeTabLocator
from .tab_locator import TabLocator
from .tab_target import TabTarget

__all__ = [
    "TAB_LOCATOR_MODEL",
    "ClaudeTabLocator",
    "TabLocator",
    "TabTarget",
    "addressable_tabs",
    "needs_vision_tabs",
    "tab_bar_present",
]
