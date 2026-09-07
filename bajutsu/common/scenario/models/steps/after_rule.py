"""One `after` entry: the teardown steps for one scenario outcome (BE-0392)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model

from .step import Step


class AfterRule(_Model):
    """One `after` entry (BE-0392): the teardown ``steps`` to run for one scenario outcome.

    ``on`` names the outcome this entry answers — ``always``, or the scenario's own machine-checked
    verdict (``success`` / ``error``). ``success``/``error`` extend the word ``capturePolicy``'s
    ``Trigger.result`` already spells for a failed outcome (there one step's, here the whole
    scenario's) rather than inventing a second vocabulary; ``always`` is the one addition, for
    cleanup that does not depend on the outcome at all. More than one entry may carry the same
    ``on`` and they compose in declaration order, the same way two ``capturePolicy`` rules may share
    a trigger. The steps share the enclosing scenario's ``vars.*``, so an entry can delete the very
    record an earlier ``http`` step's ``saveBody`` captured.
    """

    on: Literal["always", "success", "error"]
    steps: list[Step] = Field(default_factory=list)
