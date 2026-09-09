"""Tests for frontend_dist resolution across different layout schemes."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.__main__ import main as app_main
from app.core.config import Settings, resolve_frontend_dist
from app.main import create_app, main


def test_main_entry_points_match() -> None:
    assert app_main is main


def test_env_var_layout_resolution(tmp_path: Path) -> None:
    env_dist = tmp_path / "custom_ui"
    env_dist.mkdir()

    resolved = resolve_frontend_dist(
        environ={"WORKUTIL_UI_DIR": str(env_dist)},
        app_dir=tmp_path / "somewhere" / "app",
    )
    assert resolved == env_dist


def test_package_layout_resolution(tmp_path: Path) -> None:
    # Package layout: bundle/app and bundle/ui as siblings
    bundle = tmp_path / "bundle"
    app_dir = bundle / "app"
    ui_dir = bundle / "ui"
    app_dir.mkdir(parents=True)
    ui_dir.mkdir(parents=True)

    resolved = resolve_frontend_dist(environ={}, app_dir=app_dir)
    assert resolved == ui_dir


def test_repo_layout_resolution(tmp_path: Path) -> None:
    # Repo layout: repo/backend/app and repo/frontend/dist
    repo = tmp_path / "repo"
    app_dir = repo / "backend" / "app"
    dist_dir = repo / "frontend" / "dist"
    app_dir.mkdir(parents=True)
    dist_dir.mkdir(parents=True)

    resolved = resolve_frontend_dist(environ={}, app_dir=app_dir)
    assert resolved == dist_dir


def test_env_precedes_package_and_repo(tmp_path: Path) -> None:
    # When all three exist, env wins
    root = tmp_path / "test_env_prio"
    app_dir = root / "backend" / "app"
    repo_dist = root / "frontend" / "dist"
    pkg_ui = root / "backend" / "ui"
    env_ui = root / "env_ui"

    app_dir.mkdir(parents=True)
    repo_dist.mkdir(parents=True)
    pkg_ui.mkdir(parents=True)
    env_ui.mkdir(parents=True)

    resolved = resolve_frontend_dist(
        environ={"WORKUTIL_UI_DIR": str(env_ui)},
        app_dir=app_dir,
    )
    assert resolved == env_ui


def test_package_precedes_repo(tmp_path: Path) -> None:
    # When package layout and repo layout both exist, package layout wins
    # In bundle layout: bundle/app and bundle/ui
    root = tmp_path / "test_pkg_prio"
    app_dir = root / "app"
    pkg_ui = root / "ui"
    repo_dist = root.parent / "frontend" / "dist"

    app_dir.mkdir(parents=True)
    pkg_ui.mkdir(parents=True)
    repo_dist.mkdir(parents=True)

    resolved = resolve_frontend_dist(environ={}, app_dir=app_dir)
    assert resolved == pkg_ui


def test_fallback_when_none_exist_does_not_raise(tmp_path: Path) -> None:
    non_existent_app_dir = tmp_path / "empty" / "app"

    resolved = resolve_frontend_dist(environ={}, app_dir=non_existent_app_dir)
    assert not resolved.exists()

    # create_app starts normally in dev mode without throwing
    data_dir = tmp_path / "data"
    settings = Settings(data_dir=data_dir, frontend_dist=resolved)
    app = create_app(settings)
    with TestClient(app) as client:
        res = client.get("/api/memos")
        assert res.status_code == 200
