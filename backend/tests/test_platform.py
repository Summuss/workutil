import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import PlatformDep, get_platform
from app.core.platform import (
    LinuxPlatform,
    MacOSPlatform,
    Platform,
    UnsupportedPlatformError,
    WindowsPlatform,
    get_default_platform,
    get_platform_for,
)
from tests.conftest import workutil_at
from tests.fake_platform import FakePlatform, PlatformCall


def test_linux_platform_raises_unsupported_platform_error() -> None:
    platform = LinuxPlatform()

    with pytest.raises(UnsupportedPlatformError) as exc_info:
        platform.open("/home/user/document.txt")

    err = exc_info.value
    assert not isinstance(err, NotImplementedError)
    assert len(str(err).strip()) > 0
    assert "不支持" in str(err)

    with pytest.raises(UnsupportedPlatformError) as exc_info_reveal:
        platform.reveal("/home/user/document.txt")

    assert not isinstance(exc_info_reveal.value, NotImplementedError)
    assert "不支持" in str(exc_info_reveal.value)

    with pytest.raises(UnsupportedPlatformError) as exc_info_window:
        platform.open_app_window("http://127.0.0.1:8765")

    assert not isinstance(exc_info_window.value, NotImplementedError)
    assert "不支持" in str(exc_info_window.value)


@pytest.mark.skipif(
    sys.platform in ("win32", "darwin"),
    reason="exercises sys.platform dispatch on the host actually running tests",
)
def test_default_platform_on_linux_is_linux_platform() -> None:
    platform = get_default_platform()
    assert isinstance(platform, LinuxPlatform)

    with pytest.raises(UnsupportedPlatformError) as exc_info:
        platform.open(Path("/tmp/sample.txt"))

    assert not isinstance(exc_info.value, NotImplementedError)


def test_get_platform_for_different_os_names() -> None:
    assert isinstance(get_platform_for("win32"), WindowsPlatform)
    assert isinstance(get_platform_for("darwin"), MacOSPlatform)
    assert isinstance(get_platform_for("linux"), LinuxPlatform)
    assert isinstance(get_platform_for("linux2"), LinuxPlatform)
    assert isinstance(get_platform_for("freebsd"), LinuxPlatform)


def test_windows_platform_calls() -> None:
    win = WindowsPlatform()

    with patch("os.startfile", create=True) as mock_startfile:
        win.open("C:\\Users\\test\\file.txt")
        mock_startfile.assert_called_once_with("C:\\Users\\test\\file.txt")

    with patch("subprocess.Popen") as mock_popen:
        path = r"C:\Users\test\file.txt"
        win.reveal(path)
        mock_popen.assert_called_once_with(f'explorer /select,"{path}"')


def test_windows_reveal_quotes_only_the_path() -> None:
    """A path with a space is the one explorer silently gets wrong.

    Handed a list, `list2cmdline` wraps the whole `/select,...` argument in
    quotes; explorer's own parser cannot read that and opens the user's
    Documents folder rather than reporting anything. The quotes go around the
    path and nothing else.
    """
    win = WindowsPlatform()

    with patch("subprocess.Popen") as mock_popen:
        win.reveal(r"C:\Program Files\My Tool\notes.txt")

    mock_popen.assert_called_once_with(
        'explorer /select,"C:\\Program Files\\My Tool\\notes.txt"'
    )


def test_windows_reveal_hands_explorer_backslashes() -> None:
    """A bookmark registered with forward slashes still opens on Windows.

    `Path.exists()` accepts either separator, so such a path registers and
    opens fine — and then explorer, which does not, lands in Documents.
    """
    win = WindowsPlatform()

    with patch("subprocess.Popen") as mock_popen:
        win.reveal("C:/Users/test/file.txt")

    mock_popen.assert_called_once_with('explorer /select,"C:\\Users\\test\\file.txt"')


def test_macos_platform_calls() -> None:
    mac = MacOSPlatform()

    with patch("subprocess.Popen") as mock_popen:
        mac.open("/Users/test/file.txt")
        mock_popen.assert_called_once_with(["open", "/Users/test/file.txt"])

    with patch("subprocess.Popen") as mock_popen:
        mac.reveal("/Users/test/file.txt")
        mock_popen.assert_called_once_with(["open", "-R", "/Users/test/file.txt"])


def test_windows_platform_open_app_window(tmp_path: Path) -> None:
    win = WindowsPlatform()
    data_dir = tmp_path / "workutil"
    url = "http://127.0.0.1:8765"
    expected_profile = str(data_dir / "browser-profile")

    with patch("subprocess.Popen") as mock_popen:
        win.open_app_window(url, data_dir=data_dir)
        # No shell=True: on Windows that routes the call through `cmd /c`,
        # which prints "not recognized" and exits rather than making Popen()
        # raise — a missing msedge would then look like success and chrome
        # would never be tried. See the comment in platform.py.
        mock_popen.assert_called_once_with(
            ["msedge", f"--app={url}", f"--user-data-dir={expected_profile}"],
        )


def test_windows_platform_open_app_window_falls_back_past_missing_candidates(
    tmp_path: Path,
) -> None:
    """A candidate genuinely not found must be skipped, not mistaken for
    success — the bug shell=True introduced (it swallowed "not found" as a
    printed cmd.exe error instead of a raised exception, so this fallback
    chain never actually ran)."""
    win = WindowsPlatform()
    data_dir = tmp_path / "workutil"
    url = "http://127.0.0.1:8765"
    expected_profile = str(data_dir / "browser-profile")

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.side_effect = [FileNotFoundError(), None]
        win.open_app_window(url, data_dir=data_dir)

        assert mock_popen.call_count == 2
        mock_popen.assert_called_with(
            ["chrome", f"--app={url}", f"--user-data-dir={expected_profile}"],
        )


def test_macos_platform_open_app_window(tmp_path: Path) -> None:
    mac = MacOSPlatform()
    data_dir = tmp_path / "workutil"
    url = "http://127.0.0.1:8765"
    expected_profile = str(data_dir / "browser-profile")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mac.open_app_window(url, data_dir=data_dir)
        mock_run.assert_called_once_with(
            [
                "open",
                "-na",
                "Google Chrome",
                "--args",
                f"--app={url}",
                f"--user-data-dir={expected_profile}",
            ],
            check=False,
            capture_output=True,
        )


def test_fake_platform_records_calls_and_order() -> None:
    fake = FakePlatform()
    assert isinstance(fake, Platform)

    fake.open("/path/to/first.txt")
    fake.reveal("/path/to/folder")
    fake.open(Path("/path/to/second.txt"))
    fake.open_app_window("http://127.0.0.1:8765")

    assert fake.calls == [
        PlatformCall(verb="open", path="/path/to/first.txt"),
        PlatformCall(verb="reveal", path="/path/to/folder"),
        PlatformCall(verb="open", path="/path/to/second.txt"),
        PlatformCall(verb="open_app_window", path="http://127.0.0.1:8765"),
    ]
    assert fake.opened == ["/path/to/first.txt", "/path/to/second.txt"]
    assert fake.revealed == ["/path/to/folder"]
    assert fake.app_windows == ["http://127.0.0.1:8765"]

    fake.clear()
    assert fake.calls == []
    assert fake.opened == []
    assert fake.revealed == []
    assert fake.app_windows == []


def test_platform_injected_via_deps_and_substitutable(data_dir: Path) -> None:
    fake = FakePlatform()

    # 1. Injected directly into create_app
    with workutil_at(data_dir, platform=fake) as client:
        app = client.app
        assert isinstance(app, FastAPI)
        assert app.state.platform is fake

    # 2. PlatformDep resolves from request.app.state.platform
    test_app = FastAPI()
    test_app.state.platform = fake

    @test_app.post("/test-open")
    def open_endpoint(path: str, platform: PlatformDep) -> dict[str, str]:
        platform.open(path)
        return {"status": "ok"}

    with TestClient(test_app) as client:
        res = client.post("/test-open", params={"path": "/state/path.txt"})
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}
        assert fake.opened == ["/state/path.txt"]

    # 3. PlatformDep can be replaced via dependency_overrides
    another_fake = FakePlatform()
    test_app.dependency_overrides[get_platform] = lambda: another_fake
    with TestClient(test_app) as client:
        res = client.post("/test-open", params={"path": "/override/path.txt"})
        assert res.status_code == 200
        assert another_fake.opened == ["/override/path.txt"]
