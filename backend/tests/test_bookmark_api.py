"""HTTP tests for Bookmark and BookmarkGroup API.

The HTTP boundary is the agreed test seam: these drive the real application
against a temporary data directory and test all required behaviors for Ticket 02 & 03.
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

    # Move G0 down: order should become [G1, G0, G2]
    res = client.post(f"/api/bookmark-groups/{g0['id']}/move", json={"to": "down"})
    assert res.status_code == 200
    reordered = res.json()
    assert [g["name"] for g in reordered] == ["G1", "G0", "G2"]
    assert [g["order"] for g in reordered] == [0, 1, 2]

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

    # Moving top item up is no-op
    res = client.post(f"/api/bookmark-groups/{g1['id']}/move", json={"to": "up"})
    assert res.status_code == 200
    assert [g["name"] for g in res.json()] == ["G1", "G0", "G2"]


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

    # Move b0 down -> [B1, B0, B2]
    res = client.post(f"/api/bookmarks/{b0['id']}/move", json={"to": "down"})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["B1", "B0", "B2"]
    assert [b["order"] for b in res.json()] == [0, 1, 2]

    # Move b2 to top -> [B2, B1, B0]
    res = client.post(f"/api/bookmarks/{b2['id']}/move", json={"to": "top"})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["B2", "B1", "B0"]
    assert [b["order"] for b in res.json()] == [0, 1, 2]

    # Check GET /api/bookmarks maintains this order inside group
    list_res = client.get("/api/bookmarks").json()
    assert [b["name"] for b in list_res["groups"][0]["bookmarks"]] == [
        "B2",
        "B1",
        "B0",
    ]


def test_move_loose_bookmark(client: TestClient, tmp_path: Path) -> None:
    f1 = tmp_path / "1.txt"
    f1.write_text("1")
    f2 = tmp_path / "2.txt"
    f2.write_text("2")

    l0 = client.post("/api/bookmarks", json={"name": "L0", "path": str(f1)}).json()
    client.post("/api/bookmarks", json={"name": "L1", "path": str(f2)})

    res = client.post(f"/api/bookmarks/{l0['id']}/move", json={"to": "down"})
    assert res.status_code == 200
    assert [b["name"] for b in res.json()] == ["L1", "L0"]
    assert [b["order"] for b in res.json()] == [0, 1]


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
