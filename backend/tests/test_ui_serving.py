"""The built frontend, and who owns which URL.

Why any of this is needed: docs/design.md §3.1.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .conftest import workutil_at

INDEX_HTML = "<!doctype html><title>workutil</title><div id=root></div>"


def a_frontend_build(at: Path) -> Path:
    at.mkdir(parents=True, exist_ok=True)
    (at / "assets").mkdir(exist_ok=True)
    (at / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (at / "assets" / "index-abc123.js").write_text("console.log(1)\n")
    return at


@pytest.fixture
def client(data_dir: Path, tmp_path: Path) -> Iterator[TestClient]:
    """workutil with a frontend build behind it, the way `make run` has one.

    Deliberately overrides the bare `client` from conftest: every test here is
    about serving the UI, which the default settings point at the real build
    for — not something to assert against.
    """
    with workutil_at(data_dir, frontend_dist=a_frontend_build(tmp_path / "dist")) as c:
        yield c


def test_the_root_serves_the_app(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_a_frontend_route_survives_a_reload(client: TestClient) -> None:
    """Guard for ticket 01: `/evidence` has no file behind it, and reloading
    there must not 404 — the router only gets to look at the URL if the app
    itself comes back."""
    response = client.get("/evidence")

    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_a_nested_frontend_route_survives_a_reload(client: TestClient) -> None:
    """Ticket 03 puts one evidence behind `/evidence/3`, which is where you sit
    while working — so it is the URL most likely to be reloaded or bookmarked,
    and it has no file behind it either."""
    response = client.get("/evidence/3")

    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_a_reload_survives_a_404_page_in_the_build(
    data_dir: Path, tmp_path: Path
) -> None:
    """`StaticFiles` stops raising on a miss the moment the build contains a
    `404.html`, and hands one back instead. Nothing in the frontend emits that
    file today; if something ever does, reloads must not start failing."""
    dist = a_frontend_build(tmp_path / "dist")
    (dist / "404.html").write_text("<!doctype html>lost", encoding="utf-8")

    with workutil_at(data_dir, frontend_dist=dist) as client:
        response = client.get("/evidence")

    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_an_unknown_api_path_stays_a_404(client: TestClient) -> None:
    """A typo in a fetch URL must fail as a 404, not arrive as a page."""
    response = client.get("/api/nope")

    assert response.status_code == 404
    assert response.text != INDEX_HTML


def test_a_missing_asset_stays_a_404(client: TestClient) -> None:
    """Same for a stale script tag: handing it index.html turns a clear 404
    into a confusing MIME-type error in the browser console."""
    response = client.get("/assets/index-gone.js")

    assert response.status_code == 404
    assert response.text != INDEX_HTML


def test_real_assets_are_still_served(client: TestClient) -> None:
    response = client.get("/assets/index-abc123.js")

    assert response.status_code == 200
    assert response.text.strip() == "console.log(1)"
