"""The doctor id-coverage thresholds as written under `doctor:` (BE-0024)."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from ._model import _Model


class DoctorConfig(_Model):
    """Configurable thresholds for ``bajutsu doctor``'s id-coverage grading (BE-0024).

    ``idCoverageOk`` is the minimum coverage to be eligible for "Ready"; ``idCoverageFail``
    is the ceiling below which the grade drops to "Blocked". Both must be in [0, 1] with
    ok >= fail.
    """

    id_coverage_ok: float = Field(default=0.9, alias="idCoverageOk")
    id_coverage_fail: float = Field(default=0.7, alias="idCoverageFail")

    @model_validator(mode="after")
    def _ok_above_fail(self) -> DoctorConfig:
        if self.id_coverage_ok < self.id_coverage_fail:
            raise ValueError(
                f"doctor.idCoverageOk ({self.id_coverage_ok}) must be >= "
                f"doctor.idCoverageFail ({self.id_coverage_fail})"
            )
        return self

    @field_validator("id_coverage_ok", "id_coverage_fail")
    @classmethod
    def _in_unit_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"doctor threshold must be in [0, 1], got {v}")
        return v
