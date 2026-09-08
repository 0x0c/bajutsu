"""Find a screen's tab bar deterministically, and fall back to the model when it cannot."""

from __future__ import annotations

from bajutsu.common.ai import MessageResponse
from bajutsu.common.drivers import base
from bajutsu.common.screenshots import fraction

from .tab_target import TabTarget

# The accessibility label iOS auto-assigns a tab bar. iOS surfaces a SwiftUI `TabView` as a single
# container carrying this label (observed: no identifier, trait `group`) with no per-tab children —
# so the bar is on screen and tappable, but its individual tabs can't be addressed from the tree.
_TAB_BAR_LABEL = "tab bar"


def _is_tab(element: base.Element) -> bool:
    """Whether an element is a tab control named as such (`tab`, or a `tabBar` container)."""
    traits = element.get("traits") or []
    return "tab" in traits or "tabBar" in traits


def addressable_tabs(elements: list[base.Element]) -> bool:
    """Whether individual tabs are already tappable from the tree — so no vision is needed.

    Firing vision then would just duplicate those taps. Today: a tab element carrying an
    identifier, which the deterministic `candidate_actions` taps directly. UIKit support is
    provisional — see `_uikit_addressable_tabs`.
    """
    return any(_is_tab(el) and el.get("identifier") for el in elements) or _uikit_addressable_tabs(
        elements
    )


def _uikit_addressable_tabs(_elements: list[base.Element]) -> bool:
    """UIKit tab bar — provisional stub, the single place to complete once we have real UIKit tab-bar data.

    Unlike SwiftUI's opaque "Tab Bar" group, a UIKit `UITabBar` exposes each tab as its own element
    (likely a `button` with the tab's title as its label, possibly an identifier), so its tabs are
    usually addressable by selector and the deterministic guide / proposer can tap them without
    vision. We haven't yet confirmed its exact representation, so this recognizes nothing for now
    (leaving the vision fallback in charge). To complete UIKit support: capture the accessibility
    tree of a UIKit tab bar, then recognize its tab elements here (by trait / label
    / id) — `addressable_tabs` and `needs_vision_tabs` pick the result up automatically.
    """
    return False  # TODO(BE-0038): recognize UIKit UITabBarButton elements once its tree output is known


def tab_bar_present(elements: list[base.Element]) -> bool:
    """Whether a tab bar is on screen at all.

    A tab / tabBar element, or the container iOS labels "Tab Bar" (its auto-assigned accessibility
    label) — how iOS surfaces a SwiftUI TabView, as a lone `group` with that label and no
    addressable per-tab children.
    """
    for el in elements:
        if _is_tab(el):
            return True
        if (el.get("label") or "").strip().lower() == _TAB_BAR_LABEL:
            return True
    return False


def needs_vision_tabs(elements: list[base.Element]) -> bool:
    """The one case the vision locator should fire: a tab bar present but its tabs unaddressable from the tree, keeping vision off ordinary screens and id-tappable bars."""
    return tab_bar_present(elements) and not addressable_tabs(elements)


def _targets_of(response: MessageResponse, width: int, height: int) -> list[TabTarget]:
    tool_use = response.first_tool_use()
    if tool_use is None:
        return []
    out: list[TabTarget] = []
    for item in tool_use.input.get("tabs") or []:
        if not isinstance(item, dict) or item.get("x") is None or item.get("y") is None:
            continue
        out.append(
            TabTarget(
                x=fraction(float(item["x"]), width),
                y=fraction(float(item["y"]), height),
                label=str(item.get("label", "")),
            )
        )
    return out
