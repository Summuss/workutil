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


class InvalidZipArchive(ValueError):
    """The uploaded file cannot be read as a zip archive."""

    code = "transfer.invalid_zip_archive"


class ZipSlipDetected(ValueError):
    """A zip entry names a path that would write outside the data directory."""

    code = "transfer.zip_slip_detected"


class InvalidZipStructure(ValueError):
    """The zip is missing `workutil.db` or `manifest.json`."""

    code = "transfer.invalid_zip_structure"


class InvalidManifest(ValueError):
    """`manifest.json` is missing, unreadable, or not valid JSON."""

    code = "transfer.invalid_manifest"


class AlembicRevisionMismatch(ValueError):
    """The package's schema version doesn't match this install's."""

    code = "transfer.alembic_revision_mismatch"


class DatabaseNotEmpty(ValueError):
    """Import is refused because the current database already holds data."""

    code = "transfer.database_not_empty"


class ImagesNotEmpty(ValueError):
    """Import is refused because the images directory still has files."""

    code = "transfer.images_not_empty"


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
    except sqlite3.OperationalError:
        # No alembic_version table yet — an empty, unmigrated db.
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
        except sqlite3.OperationalError:
            # No alembic_version table yet — an empty, unmigrated db.
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
        raise InvalidZipArchive("上传的文件不是合法的 zip 压缩包")

    try:
        zf = zipfile.ZipFile(upload_path, "r")
    except zipfile.BadZipFile as e:
        raise InvalidZipArchive(f"无法读取 zip 压缩包：{e}") from e

    with zf:
        namelist = zf.namelist()

        # Check Zip Slip on all entries
        for name in namelist:
            if name.startswith("/") or name.startswith("\\"):
                raise ZipSlipDetected(f"压缩包条目「{name}」包含非法的绝对路径")
            parts = Path(name).parts
            if ".." in parts:
                raise ZipSlipDetected(f"压缩包条目「{name}」包含非法的目录穿越路径")

        if "manifest.json" not in namelist or "workutil.db" not in namelist:
            raise InvalidZipStructure("压缩包必须同时包含 manifest.json 与 workutil.db")

        # Gate 2: Verify alembic revision against current application
        try:
            manifest_raw = zf.read("manifest.json").decode("utf-8")
            manifest_data = json.loads(manifest_raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise InvalidManifest(f"manifest.json 无效：{e}") from e
        if not isinstance(manifest_data, dict):
            raise InvalidManifest("manifest.json 内容不是一个合法的对象")

        manifest_rev = str(manifest_data.get("alembic_revision", ""))
        current_rev = get_current_alembic_revision(settings)
        if not manifest_rev or manifest_rev != current_rev:
            raise AlembicRevisionMismatch(
                f"数据包的数据库版本（{manifest_rev}）与当前应用版本"
                f"（{current_rev}）不一致"
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
                        raise DatabaseNotEmpty(
                            f"表「{table}」还有 {count} 条数据，只能导入到空数据库"
                        )
            finally:
                conn.close()

        # Gate 4: No files exist in images/ directory
        if settings.images_dir.exists():
            image_files = [p for p in settings.images_dir.rglob("*") if p.is_file()]
            if image_files:
                raise ImagesNotEmpty(
                    f"图片目录还有 {len(image_files)} 个文件，只能导入到空的图片目录"
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
