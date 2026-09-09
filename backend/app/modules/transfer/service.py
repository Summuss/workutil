import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import Settings
from app.core.db import MIGRATIONS_DIR
from app.core.version import get_version


class TransferError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


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


def get_current_alembic_revision(settings: Settings) -> str:
    """Get the current alembic revision of the application/database."""
    if settings.db_path.exists():
        conn = sqlite3.connect(settings.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version_num FROM alembic_version LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                return str(row[0])
        except Exception:
            pass
        finally:
            conn.close()

    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(config)
    return script.get_current_head() or ""


def import_data_package(settings: Settings, upload_path: Path) -> tuple[str, bool]:
    """Import a zip package through the four gates of verification.

    Gate 1: Zip structure and Zip Slip safety (contains workutil.db and manifest.json).
    Gate 2: Manifest alembic revision matches current application revision.
    Gate 3: All business tables have 0 rows in the current database.
    Gate 4: No files exist in the images/ directory.

    If any gate fails, an exception is raised and the data directory remains untouched.
    On success, current workutil.db is renamed to workutil.db.bak-<timestamp>,
    new database and images are unpacked, and (backup_file, restart_required) returned.
    """
    # Gate 1: Check zip structure & zip slip
    if not zipfile.is_zipfile(upload_path):
        raise TransferError(
            code="INVALID_ZIP_ARCHIVE",
            message="Uploaded file is not a valid zip archive.",
        )

    try:
        zf = zipfile.ZipFile(upload_path, "r")
    except Exception as e:
        raise TransferError(
            code="INVALID_ZIP_ARCHIVE",
            message=f"Failed to read zip archive: {e}",
        ) from e

    with zf:
        namelist = zf.namelist()

        # Check Zip Slip on all entries
        for name in namelist:
            if name.startswith("/") or name.startswith("\\"):
                raise TransferError(
                    code="ZIP_SLIP_DETECTED",
                    message=f"Zip entry '{name}' contains illegal absolute path.",
                )
            parts = Path(name).parts
            if ".." in parts:
                raise TransferError(
                    code="ZIP_SLIP_DETECTED",
                    message=f"Zip entry '{name}' contains illegal '..' path traversal.",
                )

        if "manifest.json" not in namelist or "workutil.db" not in namelist:
            raise TransferError(
                code="INVALID_ZIP_STRUCTURE",
                message="Zip archive must contain both manifest.json and workutil.db.",
            )

        # Gate 2: Verify alembic revision against current application
        try:
            manifest_raw = zf.read("manifest.json").decode("utf-8")
            manifest_data = json.loads(manifest_raw)
        except Exception as e:
            raise TransferError(
                code="INVALID_MANIFEST",
                message=f"manifest.json is invalid: {e}",
            ) from e

        manifest_rev = str(manifest_data.get("alembic_revision", ""))
        current_rev = get_current_alembic_revision(settings)
        if not manifest_rev or manifest_rev != current_rev:
            raise TransferError(
                code="ALEMBIC_REVISION_MISMATCH",
                message=(
                    f"Alembic revision in manifest ('{manifest_rev}') does not match "
                    f"current system revision ('{current_rev}')."
                ),
            )

        # Gate 3: All business tables have 0 rows
        if settings.db_path.exists():
            conn = sqlite3.connect(settings.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master"
                    " WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    " AND name != 'alembic_version';"
                )
                business_tables = [row[0] for row in cursor.fetchall()]
                for table in sorted(business_tables):
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                    count = cursor.fetchone()[0]
                    if count > 0:
                        raise TransferError(
                            code="DATABASE_NOT_EMPTY",
                            message=(
                                f"Table '{table}' contains {count} rows. "
                                "Import can only proceed when all tables are empty."
                            ),
                        )
            finally:
                conn.close()

        # Gate 4: No files exist in images/ directory
        if settings.images_dir.exists():
            image_files = [p for p in settings.images_dir.rglob("*") if p.is_file()]
            if image_files:
                raise TransferError(
                    code="IMAGES_NOT_EMPTY",
                    message=(
                        f"Images directory contains {len(image_files)} file(s). "
                        "Import can only proceed when images directory has no files."
                    ),
                )

        # All four gates passed. Execute the backup and extraction.
        now_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_filename = f"workutil.db.bak-{now_str}"
        if settings.db_path.exists():
            backup_path = settings.data_dir / backup_filename
            settings.db_path.rename(backup_path)

        # Extract workutil.db
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with zf.open("workutil.db") as src, open(settings.db_path, "wb") as dst:
            shutil.copyfileobj(src, dst)

        # Extract images/ preserving relative path
        for info in zf.infolist():
            if info.is_dir():
                continue
            if info.filename.startswith("images/"):
                rel_parts = Path(info.filename).parts[1:]
                if not rel_parts:
                    continue
                dest_file = settings.images_dir.joinpath(*rel_parts)
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(dest_file, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        return backup_filename, True
