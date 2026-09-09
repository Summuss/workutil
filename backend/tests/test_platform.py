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
        mock_popen.assert_called_once_with(["explorer", f"/select,{path}"])


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
        mock_popen.assert_called_once_with(
            ["msedge", f"--app={url}", f"--user-data-dir={expected_profile}"],
            shell=True,
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
