"""The `setPickerValue` action: move a picker wheel to a given row."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class SetPickerValue(_Model):
    """`setPickerValue` action — move a picker wheel to the row whose value is `value`.

    iOS-only: a wheel-style `UIPickerView` / `UIDatePicker` exposes no separately addressable row, so
    no coordinate drag can guarantee stopping on one — XCUITest's own `adjust(toPickerWheelValue:)`
    acts on the resolved element instead, which is what makes this deterministic (BE-0356). Other
    backends have no such control and refuse it (UnsupportedAction).

    `sel` addresses exactly one wheel. A multi-component picker (a year wheel beside a month wheel)
    exposes each component as its own `pickerWheel` element, disambiguated by the `within` / `traits`
    / `index` fields every selector already carries, so `value` stays a plain string and each
    component is set by its own step.
    """

    sel: Selector
    value: str
