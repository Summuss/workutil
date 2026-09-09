import io
import re
import sqlite3
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.modules.transfer import service


def test_transfer_export_zip_content_and_cleanup(
    client: TestClient, data_dir: Path
) -> None:
    settings = Settings(data_dir=data_dir)
    # 1. Populate some data across modules
    memo_res = client.post("/api/memos", json={"body": "memo for export"})
    assert memo_res.status_code == 201

    todo_res = client.post("/api/todos", json={"title": "todo for export"})
    assert todo_res.status_code == 201

    ev_res = client.post("/api/evidence", json={"title": "evidence for export"})
    assert ev_res.status_code == 201
    evidence_id = ev_res.json()["id"]

    # Place a dummy image inside images/ directory to verify structure preservation
    dummy_img_path = settings.images_dir / "evidence" / str(evidence_id) / "test.png"
    dummy_img_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_img_path.write_bytes(b"\x89PNG\r\n\x1a\nfakeimagebytes")

    # Track temp dirs before export to verify cleanup
    import tempfile

    tmp_root = Path(tempfile.gettempdir())
    temp_dirs_before = set(tmp_root.glob("workutil-export-*"))

    res = client.get("/api/transfer/export")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"

    temp_dirs_after = set(tmp_root.glob("workutil-export-*"))
    new_dirs = temp_dirs_after - temp_dirs_before
    assert len(new_dirs) == 0, f"Temporary directories were left behind: {new_dirs}"

    # Verify filename format: workutil-data-<YYYYMMDD-HHMM>.zip
    disposition = res.headers.get("content-disposition", "")
    match = re.search(r'filename="?(workutil-data-\d{8}-\d{4}\.zip)"?', disposition)
    assert match is not None, (
        f"Disposition {disposition} does not match expected filename"
    )

    # 2. Extract and inspect zip archive
    zip_bytes = res.content
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "workutil.db" in namelist
        assert "manifest.json" in namelist
        expected_rel_img = f"images/evidence/{evidence_id}/test.png"
        assert expected_rel_img in namelist

        # Verify image content matches exactly
        assert zf.read(expected_rel_img) == b"\x89PNG\r\n\x1a\nfakeimagebytes"

        # Read and verify manifest.json
        manifest = zf.read("manifest.json").decode("utf-8")
        import json

        manifest_data = json.loads(manifest)
        assert "version" in manifest_data
        assert "alembic_revision" in manifest_data
        assert "exported_at" in manifest_data
        assert "table_counts" in manifest_data

        # Check alembic head revision matches
        src_conn = sqlite3.connect(settings.db_path)
        cur = src_conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
        expected_rev = cur.fetchone()[0]
        assert manifest_data["alembic_revision"] == expected_rev

        # Extract workutil.db and verify it opens and table counts match
        db_bytes = zf.read("workutil.db")
        temp_extracted_db = settings.data_dir / "temp_check.db"
        try:
            temp_extracted_db.write_bytes(db_bytes)
            dest_conn = sqlite3.connect(temp_extracted_db)
            dest_cur = dest_conn.cursor()

            # Compare counts between source db and exported db
            cur.execute("SELECT COUNT(*) FROM memos")
            memo_count = cur.fetchone()[0]
            dest_cur.execute("SELECT COUNT(*) FROM memos")
            assert dest_cur.fetchone()[0] == memo_count
            assert manifest_data["table_counts"]["memos"] == memo_count

            cur.execute("SELECT COUNT(*) FROM todos")
            todo_count = cur.fetchone()[0]
            dest_cur.execute("SELECT COUNT(*) FROM todos")
            assert dest_cur.fetchone()[0] == todo_count
            assert manifest_data["table_counts"]["todos"] == todo_count

            dest_conn.close()
        finally:
            src_conn.close()
            if temp_extracted_db.exists():
                temp_extracted_db.unlink()


def test_export_service_temp_dir_cleanup(data_dir: Path) -> None:
    settings = Settings(data_dir=data_dir)
    temp_dir, zip_path, filename = service.export_data_package(settings)
    assert temp_dir.exists()
    assert zip_path.exists()

    # Clean up temp_dir and verify no remnants
    import shutil

    shutil.rmtree(temp_dir)
    assert not temp_dir.exists()
