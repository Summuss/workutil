"""Platform abstraction for launching and revealing files.

Only two verbs (open and reveal); file and folder share `open`.
Windows / macOS / Linux each have an implementation, selected by sys.platform,
injected via deps.py so that tests can substitute a fake.
See design.md §3.3 and ticket 01.
"""

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class UnsupportedPlatformError(RuntimeError):
    """Raised when an operation is attempted on an unsupported platform.

    Linux development environments are headless/desktopless, and xdg-open fails
    dirty. We explicitly disallow opening/revealing on Linux so that the failure
    path is cleanly exercised (ticket 01, design.md §3.3).
    """

    DEFAULT_MESSAGE = "Linux 环境不支持直接打开或定位本地文件（开发服务器无桌面）"

    def __init__(self, message: str = DEFAULT_MESSAGE) -> None:
        super().__init__(message)
        self.message = message


@runtime_checkable
class Platform(Protocol):
    """System-level operations to open and reveal files or directories."""

    def open(self, path: str | Path) -> None:
        """Hand the path to the system to open, and do not wait or track it."""
        ...

    def reveal(self, path: str | Path) -> None:
        """Reveal the path in the system's file manager."""
        ...


class WindowsPlatform:
    """Windows implementation using os.startfile and explorer /select."""

    def open(self, path: str | Path) -> None:
        startfile: Callable[[str], Any] | None = getattr(os, "startfile", None)
        if startfile is not None:
            startfile(str(path))
        else:
            raise UnsupportedPlatformError("os.startfile 仅在 Windows 上可用")

    def reveal(self, path: str | Path) -> None:
        subprocess.Popen(["explorer", f"/select,{path}"])


class MacOSPlatform:
    """macOS implementation using the `open` command-line utility."""

    def open(self, path: str | Path) -> None:
        subprocess.Popen(["open", str(path)])

    def reveal(self, path: str | Path) -> None:
        subprocess.Popen(["open", "-R", str(path)])


class LinuxPlatform:
    """Linux implementation explicitly rejecting open/reveal on headless dev servers."""

    def open(self, path: str | Path) -> None:
        raise UnsupportedPlatformError()

    def reveal(self, path: str | Path) -> None:
        raise UnsupportedPlatformError()


def get_platform_for(name: str) -> Platform:
    """Select a platform implementation for the given sys.platform name."""
    if name == "win32":
        return WindowsPlatform()
    if name == "darwin":
        return MacOSPlatform()
    return LinuxPlatform()


def get_default_platform() -> Platform:
    """Return the platform implementation for the current running system."""
    return get_platform_for(sys.platform)
