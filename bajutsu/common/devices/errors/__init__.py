"""The platform-neutral device-error base every backend shares (BE-0260).

`run` / `crawl` / `record` / `audit` and the doctor paths catch a device fault the same way
whatever backend raised it, so the base type lives in this leaf module rather than in the iOS
`simctl` backend. The iOS (`simctl.DeviceError`) and Android (`adb.DeviceError`) errors subclass it
as siblings, so a generic `except DeviceError` handler need not import an iOS backend module just to
name the exception it catches — keeping `bajutsu` backend-agnostic (platform is a backend).

`DeviceTimeout` sits under that base for the same reason one step down (BE-0374): the run pipeline
treats a device that never answered differently from one that answered by refusing, so it needs a
neutral name for the first.
"""

from .device_error import DeviceError
from .device_timeout import DeviceTimeout

__all__ = ["DeviceError", "DeviceTimeout"]
