"""HTTP tests for Bookmark and BookmarkGroup API.

The HTTP boundary is the agreed test seam: these drive the real application
against a temporary data directory and test all required behaviors for Ticket 02 & 03.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.platform import LinuxPlatform
from tests.conftest import workutil_at
from tests.fake_platform import FakePlatform


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
    assert data["group_id"] is None
    assert data["order"] == 0
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


def test_create_bookmark_refuses_relative_path(client: TestClient) -> None:
    """A relative path resolves against the backend process's CWD, which is
    not something registration can promise stays fixed across restarts —
    reject it at registration time rather than let it silently point
    somewhere else later."""
    response = client.post(
        "/api/bookmarks",
        json={"name": "相对路径", "path": "app/main.py"},
    )
    assert response.status_code == 400
    assert "绝对路径" in response.json()["detail"]


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


def test_list_bookmarks_groups_and_loose(client: TestClient, tmp_path: Path) -> None:
    file1 = tmp_path / "f1.txt"
    file1.write_text("1")
    file2 = tmp_path / "f2.txt"
    file2.write_text("2")
    file3 = tmp_path / "f3.txt"
    file3.write_text("3")

    group = client.post("/api/bookmark-groups", json={"name": "开发组"}).json()

    # Create loose bookmarks
    client.post("/api/bookmarks", json={"name": "Loose 1", "path": str(file1)})
    client.post("/api/bookmarks", json={"name": "Loose 2", "path": str(file2)})

    # Create grouped bookmark
    client.post(
        "/api/bookmarks",
        json={"name": "Grouped 1", "path": str(file3), "group_id": group["id"]},
    )

    response = client.get("/api/bookmarks")
    assert response.status_code == 200
    data = response.json()

    assert len(data["groups"]) == 1
    assert data["groups"][0]["name"] == "开发组"
    assert len(data["groups"][0]["bookmarks"]) == 1
    assert data["groups"][0]["bookmarks"][0]["name"] == "Grouped 1"

    assert len(data["loose"]) == 2
    assert [b["name"] for b in data["loose"]] == ["Loose 1", "Loose 2"]


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
    assert not any(b["id"] == created["id"] for b in listed["loose"])


def test_delete_nonexistent_bookmark(client: TestClient) -> None:
    res = client.delete("/api/bookmarks/999999")
    assert res.status_code == 404


# --- BookmarkGroup and Ordering Tests (Ticket 03) ---


def test_create_bookmark_group(client: TestClient) -> None:
    res1 = client.post("/api/bookmark-groups", json={"name": "每日必开"})
    assert res1.status_code == 201
    g1 = res1.json()
    assert g1["name"] == "每日必开"
    assert g1["order"] == 0
    assert g1["bookmarks"] == []

    res2 = client.post("/api/bookmark-groups", json={"name": "工程项目"})
    assert res2.status_code == 201
    g2 = res2.json()
    assert g2["name"] == "工程项目"
    assert g2["order"] == 1


def test_create_bookmark_group_refuses_empty_name(client: TestClient) -> None:
    res = client.post("/api/bookmark-groups", json={"name": "   "})
    assert res.status_code == 422


def test_update_bookmark_group(client: TestClient) -> None:
    group = client.post("/api/bookmark-groups", json={"name": "原名"}).json()

    updated = client.patch(f"/api/bookmark-groups/{group['id']}", json={"name": "新名"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "新名"

    # Empty name refused
    refused = client.patch(f"/api/bookmark-groups/{group['id']}", json={"name": "  "})
    assert refused.status_code == 422

    # Nonexistent group
    missing = client.patch("/api/bookmark-groups/999999", json={"name": "测试"})
    assert missing.status_code == 404


def test_move_bookmark_group(client: TestClient) -> None:
    g0 = client.post("/api/bookmark-groups", json={"name": "G0"}).json()
    g1 = client.post("/api/bookmark-groups", json={"name": "G1"}).json()
    g2 = client.post("/api/bookmark-groups", json={"name": "G2"}).json()

    # Move G0 to middle (index 1): order should become [G1, G0, G2]
    res = client.post(f"/api/bookmark-groups/{g0['id']}/move", json={"to": 1})
    assert res.status_code == 200
    reordered = res.json()
    assert [g["name"] for g in reordered] == ["G1", "G0", "G2"]
    assert [g["order"] for g in reordered] == [0, 1, 2]

    # Move G0 to same position (index 1): no-op
    res = client.post(f"/api/bookmark-groups/{g0['id']}/move", json={"to": 1})
    assert res.status_code == 200
    assert [g["name"] for g in res.json()] == ["G1", "G0", "G2"]

    # Move G2 to top: order should become [G2, G1, G0]
    res = client.post(f"/api/bookmark-groups/{g2['id']}/move", json={"to": "top"})
    assert res.status_code == 200
    reordered = res.json()
    assert [g["name"] for g in reordered] == ["G2", "G1", "G0"]
    assert [g["order"] for g in reordered] == [0, 1, 2]

    # Move G2 to bottom: order should become [G1, G0, G2]
    res = client.post(f"/api/bookmark-groups/{g2['id']}/move", json={"to": "bottom"})
    assert res.status_code == 200
    reordered = res.json()
    assert [g["name"] for g in reordered] == ["G1", "G0", "G2"]

    # Moving to out of bounds clamps to boundary
    res = client.post(f"/api/bookmark-groups/{g2['id']}/move", json={"to": -1})
    assert res.status_code == 200
    assert [g["name"] for g in res.json()] == ["G2", "G1", "G0"]

    res = client.post(f"/api/bookmark-groups/{g2['id']}/move", json={"to": 999})
    assert res.status_code == 200
    assert [g["name"] for g in res.json()] == ["G1", "G0", "G2"]

    # Refuse up / down
    for invalid in ("up", "down", "sideways"):
        res = client.post(f"/api/bookmark-groups/{g1['id']}/move", json={"to": invalid})
        assert res.status_code == 422


def test_move_bookmark_inside_group(client: TestClient, tmp_path: Path) -> None:
    f1 = tmp_path / "1.txt"
    f1.write_text("1")
    f2 = tmp_path / "2.txt"
    f2.write_text("2")
    f3 = tmp_path / "3.txt"
    f3.write_text("3")

    group = client.post("/api/bookmark-groups", json={"name": "Group"}).json()

    b0 = client.post(
        "/api/bookmarks",
        json={"name": "B0", "path": str(f1), "group_id": group["id"]},
    ).json()
    client.post(
        "/api/bookmarks",
        json={"name": "B1", "path": str(f2), "group_id": group["id"]},
    )
    b2 = client.post(
        "/api/bookmarks",
        json={"name": "B2", "path": str(f3), "group_id": group["id"]},
    ).json()

    # Move b0 to middle (index 1) -> [B1, B0, B2]
    res = client.post(f"/api/bookmarks/{b0['id']}/move", json={"to": 1})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["B1", "B0", "B2"]
    assert [b["order"] for b in res.json()] == [0, 1, 2]

    # Move b0 to current position (index 1) -> no change
    res = client.post(f"/api/bookmarks/{b0['id']}/move", json={"to": 1})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["B1", "B0", "B2"]

    # Move b2 to top -> [B2, B1, B0]
    res = client.post(f"/api/bookmarks/{b2['id']}/move", json={"to": "top"})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["B2", "B1", "B0"]
    assert [b["order"] for b in res.json()] == [0, 1, 2]

    # Boundary clamping
    res = client.post(f"/api/bookmarks/{b2['id']}/move", json={"to": 999})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["B1", "B0", "B2"]

    res = client.post(f"/api/bookmarks/{b2['id']}/move", json={"to": -10})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["B2", "B1", "B0"]

    # Check GET /api/bookmarks maintains this order inside group
    list_res = client.get("/api/bookmarks").json()
    assert [b["name"] for b in list_res["groups"][0]["bookmarks"]] == [
        "B2",
        "B1",
        "B0",
    ]

    for invalid in ("up", "down"):
        res = client.post(f"/api/bookmarks/{b0['id']}/move", json={"to": invalid})
        assert res.status_code == 422


def test_move_loose_bookmark(client: TestClient, tmp_path: Path) -> None:
    f1 = tmp_path / "1.txt"
    f1.write_text("1")
    f2 = tmp_path / "2.txt"
    f2.write_text("2")

    l0 = client.post("/api/bookmarks", json={"name": "L0", "path": str(f1)}).json()
    client.post("/api/bookmarks", json={"name": "L1", "path": str(f2)})

    # Move l0 to index 1 -> [L1, L0]
    res = client.post(f"/api/bookmarks/{l0['id']}/move", json={"to": 1})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["L1", "L0"]
    assert [b["order"] for b in res.json()] == [0, 1]

    # Move l0 to index 1 (current) -> [L1, L0]
    res = client.post(f"/api/bookmarks/{l0['id']}/move", json={"to": 1})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["L1", "L0"]

    # Out of bounds clamping
    res = client.post(f"/api/bookmarks/{l0['id']}/move", json={"to": -1})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["L0", "L1"]

    for invalid in ("up", "down"):
        res = client.post(f"/api/bookmarks/{l0['id']}/move", json={"to": invalid})
        assert res.status_code == 422


def test_transfer_bookmark_between_groups_and_loose(
    client: TestClient, tmp_path: Path
) -> None:
    f1 = tmp_path / "1.txt"
    f1.write_text("1")
    f2 = tmp_path / "2.txt"
    f2.write_text("2")

    g1 = client.post("/api/bookmark-groups", json={"name": "G1"}).json()
    g2 = client.post("/api/bookmark-groups", json={"name": "G2"}).json()

    b1 = client.post(
        "/api/bookmarks",
        json={"name": "B1", "path": str(f1), "group_id": g1["id"]},
    ).json()
    b2 = client.post(
        "/api/bookmarks",
        json={"name": "B2", "path": str(f2), "group_id": g1["id"]},
    ).json()

    # Move b1 from G1 to G2
    transferred = client.patch(
        f"/api/bookmarks/{b1['id']}", json={"group_id": g2["id"]}
    ).json()
    assert transferred["group_id"] == g2["id"]
    assert transferred["order"] == 0

    # G1 remaining bookmark b2 renumbered to order 0
    g1_b2 = client.get(f"/api/bookmarks/{b2['id']}").json()
    assert g1_b2["order"] == 0

    # Move b1 to loose (group_id = None)
    to_loose = client.patch(
        f"/api/bookmarks/{b1['id']}", json={"group_id": None}
    ).json()
    assert to_loose["group_id"] is None
    assert to_loose["order"] == 0

    # Move b1 from loose back into G1
    back_to_g1 = client.patch(
        f"/api/bookmarks/{b1['id']}", json={"group_id": g1["id"]}
    ).json()
    assert back_to_g1["group_id"] == g1["id"]
    assert back_to_g1["order"] == 1  # appended after b2


def test_update_bookmark_name_only_does_not_change_group(
    client: TestClient, tmp_path: Path
) -> None:
    """Renaming a bookmark must not silently evict it from its group. The
    PATCH endpoint only touches group_id when the field is explicitly present
    in the request body (`model_fields_set`) — this guards that distinction
    against a future simplification that reads `payload.group_id` unconditionally."""
    sample = tmp_path / "grouped.txt"
    sample.write_text("x")
    group = client.post("/api/bookmark-groups", json={"name": "G"}).json()
    b = client.post(
        "/api/bookmarks",
        json={"name": "旧名", "path": str(sample), "group_id": group["id"]},
    ).json()

    updated = client.patch(f"/api/bookmarks/{b['id']}", json={"name": "新名"}).json()
    assert updated["name"] == "新名"
    assert updated["group_id"] == group["id"]


def test_delete_group_keeps_members_as_loose(
    client: TestClient, tmp_path: Path
) -> None:
    """ADR-0006 & Ticket 03 guard:

    Deleting a group leaves its members as loose bookmarks,
    setting group_id to null and appending them to loose list without gaps.
    """
    f0 = tmp_path / "loose.txt"
    f0.write_text("0")
    f1 = tmp_path / "1.txt"
    f1.write_text("1")
    f2 = tmp_path / "2.txt"
    f2.write_text("2")

    # One preexisting loose bookmark
    client.post("/api/bookmarks", json={"name": "Preexisting", "path": str(f0)})

    group = client.post("/api/bookmark-groups", json={"name": "待删组"}).json()
    client.post(
        "/api/bookmarks",
        json={"name": "M1", "path": str(f1), "group_id": group["id"]},
    )
    client.post(
        "/api/bookmarks",
        json={"name": "M2", "path": str(f2), "group_id": group["id"]},
    )

    del_res = client.delete(f"/api/bookmark-groups/{group['id']}")
    assert del_res.status_code == 204

    # Group is gone
    data = client.get("/api/bookmarks").json()
    assert len(data["groups"]) == 0

    # Members are now loose and preserved!
    assert len(data["loose"]) == 3
    assert [b["name"] for b in data["loose"]] == ["Preexisting", "M1", "M2"]
    assert [b["order"] for b in data["loose"]] == [0, 1, 2]
    assert all(b["group_id"] is None for b in data["loose"])


def test_delete_bookmark_in_group_renumbers_siblings(
    client: TestClient, tmp_path: Path
) -> None:
    f1 = tmp_path / "1.txt"
    f1.write_text("1")
    f2 = tmp_path / "2.txt"
    f2.write_text("2")
    f3 = tmp_path / "3.txt"
    f3.write_text("3")

    group = client.post("/api/bookmark-groups", json={"name": "G"}).json()
    client.post(
        "/api/bookmarks",
        json={"name": "B0", "path": str(f1), "group_id": group["id"]},
    )
    b1 = client.post(
        "/api/bookmarks",
        json={"name": "B1", "path": str(f2), "group_id": group["id"]},
    ).json()
    client.post(
        "/api/bookmarks",
        json={"name": "B2", "path": str(f3), "group_id": group["id"]},
    )

    # Delete b1 (the middle item)
    client.delete(f"/api/bookmarks/{b1['id']}")

    # Remaining b0 and b2 are renumbered to 0 and 1
    g = client.get("/api/bookmarks").json()["groups"][0]
    assert [b["name"] for b in g["bookmarks"]] == ["B0", "B2"]
    assert [b["order"] for b in g["bookmarks"]] == [0, 1]


# --- Ticket 04: Open and Reveal Seam Tests ---


def test_open_file_bookmark_via_fake_platform(
    data_dir: Path, tmp_path: Path, fake_platform: FakePlatform
) -> None:
    sample = tmp_path / "target.txt"
    sample.write_text("content")

    with workutil_at(data_dir, platform=fake_platform) as client:
        b = client.post(
            "/api/bookmarks",
            json={"name": "打开测试", "path": str(sample)},
        ).json()

        res = client.post(f"/api/bookmarks/{b['id']}/open")
        assert res.status_code == 200
        assert res.json()["ok"] is True
        assert fake_platform.opened == [str(sample)]


def test_open_directory_bookmark_via_fake_platform(
    data_dir: Path, tmp_path: Path, fake_platform: FakePlatform
) -> None:
    sample_dir = tmp_path / "project_dir"
    sample_dir.mkdir()

    with workutil_at(data_dir, platform=fake_platform) as client:
        b = client.post(
            "/api/bookmarks",
            json={"name": "目录书签", "path": str(sample_dir)},
        ).json()

        res = client.post(f"/api/bookmarks/{b['id']}/open")
        assert res.status_code == 200
        assert fake_platform.opened == [str(sample_dir)]


def test_open_nonexistent_bookmark_returns_400(
    data_dir: Path, tmp_path: Path, fake_platform: FakePlatform
) -> None:
    sample = tmp_path / "temp.txt"
    sample.write_text("temp")

    with workutil_at(data_dir, platform=fake_platform) as client:
        b = client.post(
            "/api/bookmarks",
            json={"name": "将被删除", "path": str(sample)},
        ).json()

        sample.unlink()  # deleted from filesystem

        res = client.post(f"/api/bookmarks/{b['id']}/open")
        assert res.status_code == 400
        assert "不存在" in res.json()["detail"]
        assert fake_platform.opened == []


def test_reveal_file_bookmark_via_fake_platform(
    data_dir: Path, tmp_path: Path, fake_platform: FakePlatform
) -> None:
    sample = tmp_path / "file.txt"
    sample.write_text("hello")

    with workutil_at(data_dir, platform=fake_platform) as client:
        b = client.post(
            "/api/bookmarks",
            json={"name": "文件定位", "path": str(sample)},
        ).json()

        res = client.post(f"/api/bookmarks/{b['id']}/reveal")
        assert res.status_code == 200
        assert fake_platform.revealed == [str(sample)]


def test_reveal_directory_bookmark_returns_422(
    data_dir: Path, tmp_path: Path, fake_platform: FakePlatform
) -> None:
    sample_dir = tmp_path / "somedir"
    sample_dir.mkdir()

    with workutil_at(data_dir, platform=fake_platform) as client:
        b = client.post(
            "/api/bookmarks",
            json={"name": "目录书签", "path": str(sample_dir)},
        ).json()

        res = client.post(f"/api/bookmarks/{b['id']}/reveal")
        assert res.status_code == 422
        assert "文件夹书签不支持" in res.json()["detail"]
        assert fake_platform.revealed == []


def test_open_group_serial_order_and_skips_stale_items(
    data_dir: Path, tmp_path: Path, fake_platform: FakePlatform
) -> None:
    f1 = tmp_path / "file1.txt"
    f1.write_text("1")
    f2 = tmp_path / "file2.txt"
    f2.write_text("2")
    f3 = tmp_path / "file3.txt"
    f3.write_text("3")

    with workutil_at(data_dir, platform=fake_platform) as client:
        group = client.post("/api/bookmark-groups", json={"name": "工作必开"}).json()
        gid = group["id"]

        b1 = client.post(
            "/api/bookmarks", json={"name": "F1", "path": str(f1), "group_id": gid}
        ).json()
        b2 = client.post(
            "/api/bookmarks", json={"name": "F2", "path": str(f2), "group_id": gid}
        ).json()
        b3 = client.post(
            "/api/bookmarks", json={"name": "F3", "path": str(f3), "group_id": gid}
        ).json()

        # Simulate f2 being stale (deleted or moved away)
        f2.unlink()

        # Open the group
        res = client.post(f"/api/bookmark-groups/{gid}/open")
        assert res.status_code == 200
        data = res.json()

        # Check summary response: opened contains F1 and F3 in order
        assert len(data["opened"]) == 2
        assert data["opened"][0]["id"] == b1["id"]
        assert data["opened"][0]["name"] == "F1"
        assert data["opened"][0]["path"] == str(f1)
        assert data["opened"][1]["id"] == b3["id"]
        assert data["opened"][1]["name"] == "F3"
        assert data["opened"][1]["path"] == str(f3)

        # Check skipped contains F2 with clear reason
        assert len(data["skipped"]) == 1
        assert data["skipped"][0]["id"] == b2["id"]
        assert data["skipped"][0]["name"] == "F2"
        assert data["skipped"][0]["path"] == str(f2)
        assert "路径不存在" in data["skipped"][0]["reason"]

        # Crucial seam assertion: fake platform received ONLY valid paths in order,
        # stale path was NEVER handed down!
        assert fake_platform.opened == [str(f1), str(f3)]


def test_open_group_skips_item_platform_refuses_to_open(
    data_dir: Path, tmp_path: Path
) -> None:
    """A real platform.open() can raise even for a path that exists — no
    application associated, permission denied, a dangling shortcut. That
    failure must be skipped like a stale path, not sink the whole group
    (the same "opened / skipped, never all-or-nothing" discipline)."""
    f1 = tmp_path / "file1.txt"
    f1.write_text("1")
    f2 = tmp_path / "file2.dat"
    f2.write_text("2")
    f3 = tmp_path / "file3.txt"
    f3.write_text("3")

    fake_platform = FakePlatform(fail_open_for={str(f2)})

    with workutil_at(data_dir, platform=fake_platform) as client:
        group = client.post("/api/bookmark-groups", json={"name": "工作必开"}).json()
        gid = group["id"]

        b1 = client.post(
            "/api/bookmarks", json={"name": "F1", "path": str(f1), "group_id": gid}
        ).json()
        b2 = client.post(
            "/api/bookmarks", json={"name": "F2", "path": str(f2), "group_id": gid}
        ).json()
        b3 = client.post(
            "/api/bookmarks", json={"name": "F3", "path": str(f3), "group_id": gid}
        ).json()

        res = client.post(f"/api/bookmark-groups/{gid}/open")
        assert res.status_code == 200
        data = res.json()

        assert [o["id"] for o in data["opened"]] == [b1["id"], b3["id"]]
        assert [s["id"] for s in data["skipped"]] == [b2["id"]]
        assert data["skipped"][0]["reason"]  # the OS's own message, not blank
        assert fake_platform.opened == [str(f1), str(f3)]


def test_open_empty_group_returns_empty_summary(
    data_dir: Path, fake_platform: FakePlatform
) -> None:
    with workutil_at(data_dir, platform=fake_platform) as client:
        group = client.post("/api/bookmark-groups", json={"name": "空组"}).json()
        res = client.post(f"/api/bookmark-groups/{group['id']}/open")
        assert res.status_code == 200
        assert res.json() == {"opened": [], "skipped": []}
        assert fake_platform.opened == []


def test_open_nonexistent_group_returns_404(
    data_dir: Path, fake_platform: FakePlatform
) -> None:
    with workutil_at(data_dir, platform=fake_platform) as client:
        res = client.post("/api/bookmark-groups/99999/open")
        assert res.status_code == 404


def test_linux_platform_error_path_returns_501(data_dir: Path, tmp_path: Path) -> None:
    # Inject LinuxPlatform explicitly rather than lean on the `client`
    # fixture's host-based default: this test is about the Linux error path
    # itself, not about which OS happens to be running `make test`.
    sample_file = tmp_path / "valid.txt"
    sample_file.write_text("hello")

    with workutil_at(data_dir, platform=LinuxPlatform()) as client:
        group = client.post("/api/bookmark-groups", json={"name": "Linux测试组"}).json()
        b = client.post(
            "/api/bookmarks",
            json={"name": "测试", "path": str(sample_file), "group_id": group["id"]},
        ).json()

        # 1. POST open -> 501
        res_open = client.post(f"/api/bookmarks/{b['id']}/open")
        assert res_open.status_code == 501
        detail_open = res_open.json()["detail"]
        assert "Linux" in detail_open or "不支持" in detail_open

        # 2. POST reveal -> 501
        res_reveal = client.post(f"/api/bookmarks/{b['id']}/reveal")
        assert res_reveal.status_code == 501
        detail_reveal = res_reveal.json()["detail"]
        assert "Linux" in detail_reveal or "不支持" in detail_reveal

        # 3. POST group open -> 501
        res_group = client.post(f"/api/bookmark-groups/{group['id']}/open")
        assert res_group.status_code == 501
        detail_group = res_group.json()["detail"]
        assert "Linux" in detail_group or "不支持" in detail_group


# --- Ticket 05: 失效检测 (Stale Detection) tests --------------------------------


def test_check_bookmarks_empty(client: TestClient) -> None:
    res = client.post("/api/bookmarks/check")
    assert res.status_code == 200
    assert res.json() == {"items": []}


def test_check_bookmarks_all_exist(client: TestClient, tmp_path: Path) -> None:
    f = tmp_path / "valid.txt"
    f.write_text("ok")
    d = tmp_path / "valid_dir"
    d.mkdir()

    b1 = client.post("/api/bookmarks", json={"name": "File", "path": str(f)}).json()
    b2 = client.post("/api/bookmarks", json={"name": "Dir", "path": str(d)}).json()

    res = client.post("/api/bookmarks/check")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) == 2

    item1 = next(i for i in items if i["id"] == b1["id"])
    assert item1["exists"] is True

    item2 = next(i for i in items if i["id"] == b2["id"])
    assert item2["exists"] is True


def test_check_bookmarks_stale_detection(client: TestClient, tmp_path: Path) -> None:
    f1 = tmp_path / "file1.txt"
    f1.write_text("1")
    f2 = tmp_path / "file2.txt"
    f2.write_text("2")

    b1 = client.post("/api/bookmarks", json={"name": "B1", "path": str(f1)}).json()
    b2 = client.post("/api/bookmarks", json={"name": "B2", "path": str(f2)}).json()

    # Delete f1 from disk — b1 is now stale
    f1.unlink()
    assert not f1.exists()

    res = client.post("/api/bookmarks/check")
    assert res.status_code == 200
    items = res.json()["items"]

    item1 = next(i for i in items if i["id"] == b1["id"])
    assert item1["exists"] is False

    item2 = next(i for i in items if i["id"] == b2["id"])
    assert item2["exists"] is True


def test_get_bookmarks_does_not_check_existence(
    client: TestClient, tmp_path: Path
) -> None:
    """Guard: GET /api/bookmarks must NOT perform existence checks.

    It returns immediately from the database without verifying whether
    paths exist on disk.
    """
    f = tmp_path / "temp.txt"
    f.write_text("content")

    b = client.post("/api/bookmarks", json={"name": "Temp", "path": str(f)}).json()

    # Delete file from disk
    f.unlink()
    assert not f.exists()

    # GET /api/bookmarks returns normally with the bookmark intact
    res = client.get("/api/bookmarks")
    assert res.status_code == 200
    data = res.json()
    loose_ids = [item["id"] for item in data["loose"]]
    assert b["id"] in loose_ids
    # Confirm BookmarkRead schema has no 'exists' field (it does not check existence)
    found = next(item for item in data["loose"] if item["id"] == b["id"])
    assert "exists" not in found


def test_check_bookmarks_with_specific_ids(client: TestClient, tmp_path: Path) -> None:
    f1 = tmp_path / "f1.txt"
    f1.write_text("1")
    f2 = tmp_path / "f2.txt"
    f2.write_text("2")
    f3 = tmp_path / "f3.txt"
    f3.write_text("3")

    b1 = client.post("/api/bookmarks", json={"name": "B1", "path": str(f1)}).json()
    b2 = client.post("/api/bookmarks", json={"name": "B2", "path": str(f2)}).json()
    b3 = client.post("/api/bookmarks", json={"name": "B3", "path": str(f3)}).json()

    f1.unlink()

    # Check only b1 and b2
    res = client.post(
        "/api/bookmarks/check",
        json={"ids": [b1["id"], b2["id"]]},
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 2
    assert {i["id"] for i in items} == {b1["id"], b2["id"]}
    assert b3["id"] not in {i["id"] for i in items}
    item1 = next(i for i in items if i["id"] == b1["id"])
    assert item1["exists"] is False
    item2 = next(i for i in items if i["id"] == b2["id"])
    assert item2["exists"] is True


def test_check_bookmarks_multiple_bookmarks_same_path(
    client: TestClient, tmp_path: Path
) -> None:
    """ADR-0006 guard: Multiple bookmarks can point to the same path.

    When that path is deleted, all bookmarks pointing to it reflect stale status.
    """
    f = tmp_path / "shared.txt"
    f.write_text("content")

    b1 = client.post("/api/bookmarks", json={"name": "Shared 1", "path": str(f)}).json()
    b2 = client.post("/api/bookmarks", json={"name": "Shared 2", "path": str(f)}).json()

    f.unlink()

    res = client.post("/api/bookmarks/check")
    assert res.status_code == 200
    items = res.json()["items"]

    item1 = next(i for i in items if i["id"] == b1["id"])
    item2 = next(i for i in items if i["id"] == b2["id"])
    assert item1["exists"] is False
    assert item2["exists"] is False
