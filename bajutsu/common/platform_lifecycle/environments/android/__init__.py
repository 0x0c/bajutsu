"""The Android emulator lifecycle via `adb` (the adb backend's environment)."""

from .android_environment import _RESIDENT_ENV as _RESIDENT_ENV
from .android_environment import AndroidEnvironment, logger
from .resident_server_like import ResidentServerLike

__all__ = ["AndroidEnvironment", "ResidentServerLike", "logger"]
