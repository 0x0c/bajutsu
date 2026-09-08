"""A scenario file: its file-level description plus the scenarios it defines."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model

from .scenario import Scenario

# The scenario file's schema version, mirroring the report manifest's SCHEMA_VERSION (BE-0119).
# Bump only for a load-breaking change: removing a required field's meaning, or a change an older
# bajutsu would misinterpret rather than merely reject. A purely additive optional field needs no
# bump — an older bajutsu simply lacks the new behavior. `load_scenario_file` compares a file's
# declared `schema` against this before validating, so a newer file fails with a clear upgrade path
# instead of an opaque extra="forbid" error.
SCHEMA_VERSION = 1


class ScenarioFile(_Model):
    """A scenario file: an optional file-level `description` plus the scenarios it defines.

    Two on-disk forms are accepted: the bare list of scenarios (no file description), or a
    `{description: "...", scenarios: [...]}` mapping.
    """

    # Named `schema` on disk (aliased to avoid shadowing BaseModel.schema). A file omitting it is
    # implicitly version 1; the version gate in load_scenario_file runs before this field validates
    # (BE-0119).
    schema_version: int = Field(default=SCHEMA_VERSION, alias="schema")
    description: str | None = None
    scenarios: list[Scenario]
