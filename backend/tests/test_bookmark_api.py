"""HTTP tests for Bookmark API.

The HTTP boundary is the agreed test seam: these drive the real application
against a temporary data directory and test all required behaviors for Ticket 02.
"""

from pathlib import Path

from fastapi.testclient import TestClient


def test_create_file_bookmark(client: TestClient, tmp_path: Path) -> None:
    sample_file = tmp_path / "test.txt"
    sample_file.write_text("hello")

    response = client.post(
        "/api/bookmarks",
        json={"name": "测试文件", "path": str(sample_file)},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "测试文件"
    assert data["path"] == str(sample_file)
    assert data["is_directory"] is False
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_directory_bookmark(client: TestClient, tmp_path: Path) -> None:
    sample_dir = tmp_path / "my_folder"
    sample_dir.mkdir()

    response = client.post(
        "/api/bookmarks",
        json={"name": "我的文件夹", "path": str(sample_dir)},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "我的文件夹"
    assert data["path"] == str(sample_dir)
    assert data["is_directory"] is True


def test_create_bookmark_refuses_nonexistent_path(
    client: TestClient, tmp_path: Path
) -> None:
    missing_path = tmp_path / "does_not_exist.txt"

    response = client.post(
        "/api/bookmarks",
        json={"name": "不存在的文件", "path": str(missing_path)},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "这个路径现在不存在"


def test_create_bookmark_strips_surrounding_quotes(
    client: TestClient, tmp_path: Path
) -> None:
    sample_file = tmp_path / "quoted.txt"
    sample_file.write_text("content")

    # Windows "Copy as Path" wraps path in double quotes
    quoted_path = f'"{sample_file}"'
    response = client.post(
        "/api/bookmarks",
        json={"name": "带引号路径", "path": quoted_path},
    )
    assert response.status_code == 201
    assert response.json()["path"] == str(sample_file)


def test_same_path_can_be_registered_multiple_times(
    client: TestClient, tmp_path: Path
) -> None:
    """ADR-0006 guard: Bookmarks are entries, not files.

    No UNIQUE constraint and no duplicate warnings.
    """
    shared_file = tmp_path / "shared.yml"
    shared_file.write_text("config: 1")

    res1 = client.post(
        "/api/bookmarks",
        json={"name": "入口一", "path": str(shared_file)},
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/bookmarks",
        json={"name": "入口二", "path": str(shared_file)},
    )
    assert res2.status_code == 201

    assert res1.json()["id"] != res2.json()["id"]
    assert res1.json()["path"] == res2.json()["path"] == str(shared_file)


def test_create_bookmark_refuses_empty_name(client: TestClient, tmp_path: Path) -> None:
    sample_file = tmp_path / "valid.txt"
    sample_file.write_text("valid")

    response = client.post(
        "/api/bookmarks",
        json={"name": "   ", "path": str(sample_file)},
    )
    assert response.status_code == 422


def test_list_bookmarks(client: TestClient, tmp_path: Path) -> None:
    file1 = tmp_path / "f1.txt"
    file1.write_text("1")
    file2 = tmp_path / "f2.txt"
    file2.write_text("2")

    client.post("/api/bookmarks", json={"name": "One", "path": str(file1)})
    client.post("/api/bookmarks", json={"name": "Two", "path": str(file2)})

    response = client.get("/api/bookmarks")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert [item["name"] for item in items] == ["Two", "One"]


def test_get_bookmark(client: TestClient, tmp_path: Path) -> None:
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("data")

    created = client.post(
        "/api/bookmarks",
        json={"name": "Sample", "path": str(sample_file)},
    ).json()

    fetched = client.get(f"/api/bookmarks/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]
    assert fetched.json()["name"] == "Sample"

    missing = client.get("/api/bookmarks/999999")
    assert missing.status_code == 404


def test_update_bookmark_name(client: TestClient, tmp_path: Path) -> None:
    sample_file = tmp_path / "update.txt"
    sample_file.write_text("data")

    created = client.post(
        "/api/bookmarks",
        json={"name": "Old Name", "path": str(sample_file)},
    ).json()

    updated = client.patch(
        f"/api/bookmarks/{created['id']}",
        json={"name": "New Name"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "New Name"
    assert updated.json()["path"] == str(sample_file)


def test_update_bookmark_path(client: TestClient, tmp_path: Path) -> None:
    file1 = tmp_path / "file1.txt"
    file1.write_text("1")
    dir2 = tmp_path / "dir2"
    dir2.mkdir()

    created = client.post(
        "/api/bookmarks",
        json={"name": "Entry", "path": str(file1)},
    ).json()
    assert created["is_directory"] is False

    updated = client.patch(
        f"/api/bookmarks/{created['id']}",
        json={"path": str(dir2)},
    )
    assert updated.status_code == 200
    assert updated.json()["path"] == str(dir2)
    assert updated.json()["is_directory"] is True


def test_update_bookmark_refuses_nonexistent_path(
    client: TestClient, tmp_path: Path
) -> None:
    file1 = tmp_path / "file1.txt"
    file1.write_text("1")

    created = client.post(
        "/api/bookmarks",
        json={"name": "Entry", "path": str(file1)},
    ).json()

    missing = tmp_path / "does_not_exist"
    updated = client.patch(
        f"/api/bookmarks/{created['id']}",
        json={"path": str(missing)},
    )
    assert updated.status_code == 400
    assert updated.json()["detail"] == "这个路径现在不存在"


def test_update_bookmark_refuses_empty_name(client: TestClient, tmp_path: Path) -> None:
    file1 = tmp_path / "file1.txt"
    file1.write_text("1")

    created = client.post(
        "/api/bookmarks",
        json={"name": "Entry", "path": str(file1)},
    ).json()

    updated = client.patch(
        f"/api/bookmarks/{created['id']}",
        json={"name": "  "},
    )
    assert updated.status_code == 422


def test_update_nonexistent_bookmark(client: TestClient, tmp_path: Path) -> None:
    file1 = tmp_path / "file1.txt"
    file1.write_text("1")

    updated = client.patch(
        "/api/bookmarks/999999",
        json={"name": "New", "path": str(file1)},
    )
    assert updated.status_code == 404


def test_delete_bookmark(client: TestClient, tmp_path: Path) -> None:
    sample_file = tmp_path / "delete.txt"
    sample_file.write_text("data")

    created = client.post(
        "/api/bookmarks",
        json={"name": "To Delete", "path": str(sample_file)},
    ).json()

    res = client.delete(f"/api/bookmarks/{created['id']}")
    assert res.status_code == 204

    # Verify gone
    get_res = client.get(f"/api/bookmarks/{created['id']}")
    assert get_res.status_code == 404

    listed = client.get("/api/bookmarks").json()
    assert not any(b["id"] == created["id"] for b in listed)


def test_delete_nonexistent_bookmark(client: TestClient) -> None:
    res = client.delete("/api/bookmarks/999999")
    assert res.status_code == 404
