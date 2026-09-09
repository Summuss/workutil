import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.config import Settings
from app.core.version import get_version


def export_data_package(settings: Settings) -> tuple[Path, Path, str]:
    """Export SQLite database, images, and manifest into a temporary zip package.

    Must use sqlite3.Connection.backup rather than plain file copy, because
    the database runs with default rollback journal (no WAL). Copying during
    an in-flight write would risk producing a corrupted database snapshot.

    Returns:
        (temp_dir, zip_path, filename)
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="workutil-export-"))
    now = datetime.now()
    filename = f"workutil-data-{now.strftime('%Y%m%d-%H%M')}.zip"
    zip_path = temp_dir / filename

    # 1. Snapshot database using sqlite3.Connection.backup
    snapshot_db_path = temp_dir / "workutil.db"
    if settings.db_path.exists():
        src_conn = sqlite3.connect(settings.db_path)
        dest_conn = sqlite3.connect(snapshot_db_path)
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()
    else:
        conn = sqlite3.connect(snapshot_db_path)
        conn.close()

    # 2. Query snapshot database for manifest info
    conn = sqlite3.connect(snapshot_db_path)
    cursor = conn.cursor()
    revision = ""
    try:
        cursor.execute("SELECT version_num FROM alembic_version LIMIT 1")
        row = cursor.fetchone()
        if row:
            revision = str(row[0])
    except Exception:
        pass

    cursor.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = [row[0] for row in cursor.fetchall()]
    table_counts: dict[str, int] = {}
    for table in sorted(tables):
        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        table_counts[table] = int(cursor.fetchone()[0])
    conn.close()

    manifest_data = {
        "version": get_version(),
        "alembic_revision": revision,
        "exported_at": now.isoformat(),
        "table_counts": table_counts,
    }

    # 3. Create zip file
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Add workutil.db
        zf.write(snapshot_db_path, arcname="workutil.db")

        # Add manifest.json
        zf.writestr(
            "manifest.json",
            json.dumps(manifest_data, ensure_ascii=False, indent=2),
        )

        # Add images/ preserving relative structure
        if settings.images_dir.is_dir():
            for root, _, files in os.walk(settings.images_dir):
                for file_name in files:
                    file_path = Path(root) / file_name
                    rel_path = file_path.relative_to(settings.images_dir).as_posix()
                    zf.write(file_path, arcname=f"images/{rel_path}")

    # Remove the unzipped snapshot db to free disk space immediately
    if snapshot_db_path.exists():
        snapshot_db_path.unlink()

    return temp_dir, zip_path, filename
