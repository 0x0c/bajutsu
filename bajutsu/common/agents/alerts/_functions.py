"""Read a locator's tool call back into an alert decision."""

from __future__ import annotations

from bajutsu.common.ai import MessageResponse
from bajutsu.common.screenshots import fraction

from .alert_decision import AlertDecision


def _decision_of(response: MessageResponse, width: int, height: int) -> AlertDecision:
    tool_use = response.first_tool_use()
    if tool_use is None or not tool_use.input.get("present"):
        return AlertDecision(present=False)
    args = tool_use.input
    raw_x, raw_y = args.get("x"), args.get("y")
    return AlertDecision(
        present=True,
        x=0.5 if raw_x is None else fraction(float(raw_x), width),
        y=0.5 if raw_y is None else fraction(float(raw_y), height),
        label=str(args.get("label", "")),
    )
