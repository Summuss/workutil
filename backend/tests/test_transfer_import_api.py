import io
import json
import sqlite3
import zipfile
from pathlib import Path

from app.core.config import Settings
from tests.conftest import workutil_at


def test_transfer_import_roundtrip(data_dir: Path, tmp_path: Path) -> None:
    """Roundtrip test: create data in export_dir, export, import into clean import_dir,

    and verify all memos, todos, bookmarks, evidence, and images are restored.
    """
    export_dir = tmp_path / "export_data"
    import_dir = tmp_path / "import_data"

    export_settings = Settings(data_dir=export_dir)
    import_settings = Settings(data_dir=import_dir)

    # 1. Populate data in export instance
    with workutil_at(export_dir) as client_exp:
        memo_res = client_exp.post("/api/memos", json={"body": "roundtrip memo"})
        assert memo_res.status_code == 201
        memo_id = memo_res.json()["id"]

        todo_res = client_exp.post("/api/todos", json={"title": "roundtrip todo"})
        assert todo_res.status_code == 201
        todo_id = todo_res.json()["id"]

        grp_res = client_exp.post("/api/bookmark-groups", json={"name": "test group"})
        assert grp_res.status_code == 201
        grp_id = grp_res.json()["id"]

        real_path = str(export_dir)
        bm_res = client_exp.post(
            "/api/bookmarks",
            json={
                "group_id": grp_id,
                "name": "roundtrip bookmark",
                "path": real_path,
            },
        )
        assert bm_res.status_code == 201
        bm_id = bm_res.json()["id"]

        ev_res = client_exp.post("/api/evidence", json={"title": "roundtrip evidence"})
        assert ev_res.status_code == 201
        evidence_id = ev_res.json()["id"]

        # Put an image for evidence
        dummy_img_path = (
            export_settings.images_dir / "evidence" / str(evidence_id) / "snap.png"
        )
        dummy_img_path.parent.mkdir(parents=True, exist_ok=True)
        dummy_img_content = b"\x89PNG\r\n\x1a\nroundtripimagebytes"
        dummy_img_path.write_bytes(dummy_img_content)

        # Export package
        exp_res = client_exp.get("/api/transfer/export")
        assert exp_res.status_code == 200
        zip_bytes = exp_res.content

    # 2. Launch clean target instance and import package
    with workutil_at(import_dir) as client_imp:
        # Check that import_dir initially has empty business tables
        init_files_before = set(import_dir.iterdir())
        assert import_settings.db_path in init_files_before

        # Upload zip
        files = {"file": ("backup.zip", io.BytesIO(zip_bytes), "application/zip")}
        imp_res = client_imp.post("/api/transfer/import", files=files)
        assert imp_res.status_code == 200, imp_res.text
        data = imp_res.json()
        assert data["restart_required"] is True
        assert "workutil.db.bak-" in data["backup_file"]

        # Check backup file exists on disk
        bak_file_path = import_dir / data["backup_file"]
        assert bak_file_path.exists()

        # Check evidence image was unpacked
        unpacked_img = (
            import_settings.images_dir / "evidence" / str(evidence_id) / "snap.png"
        )
        assert unpacked_img.exists()
        assert unpacked_img.read_bytes() == dummy_img_content

    # 3. Read the imported db to verify data integrity
    conn = sqlite3.connect(import_settings.db_path)
    cur = conn.cursor()

    cur.execute("SELECT body FROM memos WHERE id = ?", (memo_id,))
    assert cur.fetchone()[0] == "roundtrip memo"

    cur.execute("SELECT title FROM todos WHERE id = ?", (todo_id,))
    assert cur.fetchone()[0] == "roundtrip todo"

    cur.execute("SELECT name FROM bookmark_groups WHERE id = ?", (grp_id,))
    assert cur.fetchone()[0] == "test group"

    cur.execute("SELECT name, path FROM bookmarks WHERE id = ?", (bm_id,))
    row = cur.fetchone()
    assert row[0] == "roundtrip bookmark"
    assert row[1] == real_path

    cur.execute("SELECT title FROM evidence WHERE id = ?", (evidence_id,))
    assert cur.fetchone()[0] == "roundtrip evidence"

    conn.close()


def test_reject_when_database_not_empty(data_dir: Path, tmp_path: Path) -> None:
    settings = Settings(data_dir=data_dir)
    with workutil_at(data_dir) as client:
        # Create a todo so db is non-empty
        client.post("/api/todos", json={"title": "existing todo"})

        # Record directory snapshot
        files_before = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}

        # Create a dummy valid zip
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("workutil.db", b"")
            zf.writestr("manifest.json", b'{"alembic_revision": "test"}')

        res = client.post(
            "/api/transfer/import",
            files={"file": ("test.zip", zip_buf.getvalue(), "application/zip")},
        )
        # Note: manifest check happens before gate 3.
        # Ensure revision matches so it passes gate 2 and fails at gate 3.
        cur_conn = sqlite3.connect(settings.db_path)
        cur = cur_conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
        rev = cur.fetchone()[0]
        cur_conn.close()

        zip_buf2 = io.BytesIO()
        with zipfile.ZipFile(zip_buf2, "w") as zf:
            zf.writestr("workutil.db", b"")
            zf.writestr("manifest.json", json.dumps({"alembic_revision": rev}))

        res = client.post(
            "/api/transfer/import",
            files={"file": ("test.zip", zip_buf2.getvalue(), "application/zip")},
        )
        assert res.status_code == 400
        err = res.json()
        assert err["code"] == "DATABASE_NOT_EMPTY"

        # Ensure data directory was not modified (no backup created, no overwrite)
        files_after = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}
        assert files_before == files_after


def test_reject_when_images_not_empty(data_dir: Path) -> None:
    settings = Settings(data_dir=data_dir)
    with workutil_at(data_dir) as client:
        # Ensure db is empty, but place a file in images/
        img_file = settings.images_dir / "leftover.png"
        img_file.parent.mkdir(parents=True, exist_ok=True)
        img_file.write_bytes(b"leftover")

        files_before = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}

        cur_conn = sqlite3.connect(settings.db_path)
        cur = cur_conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
        rev = cur.fetchone()[0]
        cur_conn.close()

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("workutil.db", b"")
            zf.writestr("manifest.json", json.dumps({"alembic_revision": rev}))

        res = client.post(
            "/api/transfer/import",
            files={"file": ("test.zip", zip_buf.getvalue(), "application/zip")},
        )
        assert res.status_code == 400
        err = res.json()
        assert err["code"] == "IMAGES_NOT_EMPTY"

        # Assert data dir untouched
        files_after = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}
        assert files_before == files_after


def test_reject_when_alembic_revision_mismatch(data_dir: Path) -> None:
    with workutil_at(data_dir) as client:
        files_before = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("workutil.db", b"")
            zf.writestr(
                "manifest.json", json.dumps({"alembic_revision": "incompatible_rev"})
            )

        res = client.post(
            "/api/transfer/import",
            files={"file": ("test.zip", zip_buf.getvalue(), "application/zip")},
        )
        assert res.status_code == 400
        err = res.json()
        assert err["code"] == "ALEMBIC_REVISION_MISMATCH"

        files_after = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}
        assert files_before == files_after


def test_reject_when_zip_structure_invalid(data_dir: Path) -> None:
    with workutil_at(data_dir) as client:
        files_before = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}

        # 1. Not a zip archive
        res = client.post(
            "/api/transfer/import",
            files={"file": ("test.zip", b"plain string not a zip", "application/zip")},
        )
        assert res.status_code == 400
        assert res.json()["code"] == "INVALID_ZIP_ARCHIVE"

        # 2. Missing workutil.db
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("manifest.json", b"{}")
        res = client.post(
            "/api/transfer/import",
            files={"file": ("test.zip", zip_buf.getvalue(), "application/zip")},
        )
        assert res.status_code == 400
        assert res.json()["code"] == "INVALID_ZIP_STRUCTURE"

        files_after = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}
        assert files_before == files_after


def test_reject_when_zip_contains_path_traversal(data_dir: Path) -> None:
    with workutil_at(data_dir) as client:
        files_before = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("../evil.txt", b"evil")
            zf.writestr("workutil.db", b"")
            zf.writestr("manifest.json", b"{}")

        res = client.post(
            "/api/transfer/import",
            files={"file": ("test.zip", zip_buf.getvalue(), "application/zip")},
        )
        assert res.status_code == 400
        assert res.json()["code"] == "ZIP_SLIP_DETECTED"

        files_after = {p.name: p.stat().st_mtime_ns for p in data_dir.rglob("*")}
        assert files_before == files_after
