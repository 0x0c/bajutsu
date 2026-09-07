"""Where the resident server's two APKs live, and the logger its lifecycle reports through."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("bajutsu.adb.resident")


# APK build outputs of `make -C BajutsuAndroidUIAutomatorServer build` (gitignored; the paths gradle
# writes).
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SERVER_APK = (
    _REPO_ROOT / "BajutsuAndroidUIAutomatorServer/server/build/outputs/apk/debug/server-debug.apk"
)
_TEST_APK = (
    _REPO_ROOT / "BajutsuAndroidUIAutomatorServer/server/build/outputs/apk/androidTest/debug"
    "/server-debug-androidTest.apk"
)
