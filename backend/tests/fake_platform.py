"""A recording fake platform for testing bookmark opening and revealing."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class PlatformCall:
    verb: Literal["open", "reveal", "open_app_window"]
    path: str


class FakePlatform:
    """Records open, reveal, and open_app_window calls in memory for test assertions."""

    def __init__(self, fail_open_for: set[str] | None = None) -> None:
        self.calls: list[PlatformCall] = []
        self.opened: list[str] = []
        self.revealed: list[str] = []
        self.app_windows: list[str] = []
        #: Paths that should behave like a real machine refusing to open them
        #: (no application associated, permission denied, ...) — os.startfile
        #: raises OSError in exactly this shape, and open_group must survive it.
        self._fail_open_for = fail_open_for or set()

    def open(self, path: str | Path) -> None:
        p = str(path)
        if p in self._fail_open_for:
            raise OSError(1155, "No application is associated with this file")
        self.calls.append(PlatformCall(verb="open", path=p))
        self.opened.append(p)

    def reveal(self, path: str | Path) -> None:
        p = str(path)
        self.calls.append(PlatformCall(verb="reveal", path=p))
        self.revealed.append(p)

    def open_app_window(self, url: str, data_dir: Path | None = None) -> None:
        self.calls.append(PlatformCall(verb="open_app_window", path=url))
        self.app_windows.append(url)

    def clear(self) -> None:
        self.calls.clear()
        self.opened.clear()
        self.revealed.clear()
        self.app_windows.clear()
