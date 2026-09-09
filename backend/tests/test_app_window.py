"""Tests for browser app window launching and single-instance behavior."""

import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import HOST, Settings
from app.main import create_app, main, run_app
from tests.fake_platform import FakePlatform


def test_packaged_mode_opens_window_on_startup(
    monkeypatch: pytest.MonkeyPatch, data_dir: Path
) -> None:
    monkeypatch.setenv("WORKUTIL_OPEN_WINDOW", "1")
    fake = FakePlatform()
    settings = Settings(data_dir=data_dir)

    with TestClient(create_app(settings, platform=fake)):
        assert fake.app_windows == ["http://127.0.0.1:8765"]


def test_unpackaged_mode_does_not_open_window_on_startup(
    monkeypatch: pytest.MonkeyPatch, data_dir: Path
) -> None:
    monkeypatch.delenv("WORKUTIL_OPEN_WINDOW", raising=False)
    fake = FakePlatform()
    settings = Settings(data_dir=data_dir)

    with TestClient(create_app(settings, platform=fake)):
        assert fake.app_windows == []


def test_port_in_use_exits_zero_and_opens_window(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    data_dir: Path,
) -> None:
    monkeypatch.setenv("WORKUTIL_OPEN_WINDOW", "1")
    fake = FakePlatform()
    settings = Settings(data_dir=data_dir)

    # Bind a socket to an ephemeral port to simulate an already-running instance
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, 0))
        s.listen(1)
        bound_port = s.getsockname()[1]

        exit_code = run_app(
            settings=settings, platform=fake, host=HOST, port=bound_port
        )

    assert exit_code == 0
    assert fake.app_windows == [f"http://127.0.0.1:{bound_port}"]
    captured = capsys.readouterr()
    assert "已经在运行" in captured.out


def test_port_in_use_without_open_window_flag(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    data_dir: Path,
) -> None:
    monkeypatch.delenv("WORKUTIL_OPEN_WINDOW", raising=False)
    fake = FakePlatform()
    settings = Settings(data_dir=data_dir)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, 0))
        s.listen(1)
        bound_port = s.getsockname()[1]

        exit_code = main(settings=settings, platform=fake, host=HOST, port=bound_port)

    assert exit_code == 0
    assert fake.app_windows == []
    captured = capsys.readouterr()
    assert "已经在运行" in captured.out
