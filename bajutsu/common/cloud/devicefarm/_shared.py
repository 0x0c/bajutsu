"""The polling intervals and payload names the Device Farm submitter works to."""

from __future__ import annotations

# Device Farm's APPIUM_PYTHON_TEST_PACKAGE validation requires a `requirements.txt` at the package
# root (alongside a `tests/` directory). Bajutsu is a pyproject/uv project with no such file, and the
# custom test spec installs it directly (`pip install "$DEVICEFARM_TEST_PACKAGE_PATH"`), so we
# synthesize an empty one purely to satisfy the structural check rather than pin anything here.
REQUIREMENTS_TXT = (
    "# Present only to satisfy Device Farm's APPIUM_PYTHON_TEST_PACKAGE validation.\n"
    '# Bajutsu is installed by the custom test spec (pip install "$DEVICEFARM_TEST_PACKAGE_PATH"),\n'
    "# so no runtime dependencies are pinned here.\n"
)
