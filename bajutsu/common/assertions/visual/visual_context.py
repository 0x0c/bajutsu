"""What a visual assertion reads, and where the images it produces go."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bajutsu.common.drivers import base
from bajutsu.common.evidence.sink import RunArtifactWriter


@dataclass(frozen=True)
class VisualContext:
    """What a visual assertion reads, and where the images it produces go.

    `screenshot_path` is the run's captured screenshot and `baselines_dir` the project's stored
    baselines, which live outside the run directory and are only ever read. Everything written goes
    through `writer` under `prefix` — the scenario's evidence dir — so this holds no writable handle
    into the run directory (BE-0331).
    """

    screenshot_path: Path
    baselines_dir: Path
    writer: RunArtifactWriter
    prefix: str
    default_compare: str = "exact"

    @property
    def actual_name(self) -> str:
        """The captured screenshot's artifact name, relative to the run dir."""
        return f"{self.prefix}/{self.screenshot_path.name}"

    def capture_actual(self, driver: base.Driver) -> None:
        """Capture the screenshot this scenario's `visual` assertions compare against.

        The driver writes the image itself, so the sink reserves the path and records the bytes as
        uninspected — pixels cannot be masked (BE-0151).
        """
        driver.screenshot(str(self.screenshot_path))
        self.writer.record_unmasked(self.actual_name)
