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
from pathlib import Path, PureWindowsPath
from typing import Any, Protocol, runtime_checkable


class UnsupportedPlatformError(RuntimeError):
    """Raised when an operation is attempted on an unsupported platform.

    Linux development environments are headless/desktopless, and xdg-open fails
    dirty. We explicitly disallow opening/revealing on Linux so that the failure
    path is cleanly exercised (ticket 01, design.md §3.3).
    """

    code = "platform.unsupported"

    DEFAULT_MESSAGE = "Linux 环境不支持直接打开或定位本地文件（开发服务器无桌面）"

    def __init__(self, message: str = DEFAULT_MESSAGE) -> None:
        super().__init__(message)
        self.message = message


@runtime_checkable
class Platform(Protocol):
    """System-level operations to open and reveal files, and open app windows."""

    def open(self, path: str | Path) -> None:
        """Hand the path to the system to open, and do not wait or track it."""
        ...

    def reveal(self, path: str | Path) -> None:
        """Reveal the path in the system's file manager."""
        ...

    def open_app_window(self, url: str, data_dir: Path | None = None) -> None:
        """Open the URL in a standalone app window using the browser's app mode."""
        ...


def _resolve_profile_dir(data_dir: Path | None) -> Path:
    if data_dir is None:
        from app.core.config import load_settings

        data_dir = load_settings().data_dir
    profile_dir = data_dir / "browser-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir


class WindowsPlatform:
    """Windows implementation using os.startfile, explorer, and browser app mode."""

    def open(self, path: str | Path) -> None:
        startfile: Callable[[str], Any] | None = getattr(os, "startfile", None)
        if startfile is not None:
            startfile(str(path))
        else:
            raise UnsupportedPlatformError("os.startfile 仅在 Windows 上可用")

    def reveal(self, path: str | Path) -> None:
        # explorer parses its own command line rather than taking argv as it
        # was handed, and the one form it reliably understands is
        # `/select,"<path>"` — the quotes around the path alone, backslashes
        # throughout. A list is exactly what it cannot take: the moment the
        # path holds a space, list2cmdline quotes the whole
        # `"/select,C:\Some Folder\a.txt"` argument, explorer's own parser
        # gives up on it — and it does not say so. It opens the user's
        # Documents folder as if that were what was asked for, which is what
        # this looked like from the outside.
        #
        # PureWindowsPath rather than the string as stored, for the second
        # half of the same problem: a bookmark registered from a path written
        # with forward slashes (copied out of a config file, say) exists as
        # far as `Path.exists()` is concerned, and lands explorer in Documents
        # just the same.
        target = PureWindowsPath(path)
        subprocess.Popen(f'explorer /select,"{target}"')

    def open_app_window(self, url: str, data_dir: Path | None = None) -> None:
        profile_path = _resolve_profile_dir(data_dir)
        candidates = [
            ["msedge", f"--app={url}", f"--user-data-dir={profile_path}"],
            ["chrome", f"--app={url}", f"--user-data-dir={profile_path}"],
        ]
        for cmd in candidates:
            try:
                # No shell=True here: on Windows that runs the command via
                # `cmd /c`, which prints "not recognized" and exits — it does
                # NOT make Popen() raise. A missing msedge would then look
                # like success, this loop would return on the first
                # candidate, and chrome (and the real browser-tab fallback
                # below) would never be tried.
                subprocess.Popen(cmd)
                return
            except (FileNotFoundError, OSError):
                continue

        startfile: Callable[[str], Any] | None = getattr(os, "startfile", None)
        if startfile is not None:
            try:
                startfile(url)
                return
            except OSError:
                pass
        subprocess.Popen(f'start "" "{url}"', shell=True)


class MacOSPlatform:
    """macOS implementation using the `open` command-line utility."""

    def open(self, path: str | Path) -> None:
        subprocess.Popen(["open", str(path)])

    def reveal(self, path: str | Path) -> None:
        subprocess.Popen(["open", "-R", str(path)])

    def open_app_window(self, url: str, data_dir: Path | None = None) -> None:
        profile_path = _resolve_profile_dir(data_dir)
        for app in ("Google Chrome", "Microsoft Edge"):
            res = subprocess.run(
                [
                    "open",
                    "-na",
                    app,
                    "--args",
                    f"--app={url}",
                    f"--user-data-dir={profile_path}",
                ],
                check=False,
                capture_output=True,
            )
            if res.returncode == 0:
                return

        subprocess.Popen(["open", url])


class LinuxPlatform:
    """Linux implementation explicitly rejecting open/reveal/app_window."""

    def open(self, path: str | Path) -> None:
        raise UnsupportedPlatformError()

    def reveal(self, path: str | Path) -> None:
        raise UnsupportedPlatformError()

    def open_app_window(self, url: str, data_dir: Path | None = None) -> None:
        msg = "Linux 环境不支持打开独立应用窗口（开发服务器无桌面）"
        raise UnsupportedPlatformError(msg)


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
