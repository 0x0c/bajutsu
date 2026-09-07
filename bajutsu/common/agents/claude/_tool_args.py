"""The argument object of any action tool call, as the model fills it in."""

from __future__ import annotations

from ._assertion_args import _AssertionArgs
from ._target_args import _TargetArgs


class _ToolArgs(_TargetArgs, total=False):
    """The argument object of any tool/action call, as the model fills it in.

    One permissive shape across every tool — a given tool's `input_schema` fixes which of these it
    actually populates, so each field is optional here and read only on the branch that expects it.
    """

    reason: str
    plan_step: int
    x: float
    y: float
    direction: str
    amount: float
    text: str
    timeout: float
    assertions: list[_AssertionArgs]
    prompt: str
    classify: str
    name: str
    bypass: str
