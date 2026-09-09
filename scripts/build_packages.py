#!/usr/bin/env python3
"""Assemble portable packages for Windows and macOS on Linux.

Builds self-contained zip archives by combining:
1. python-build-standalone runtime
2. Precompiled wheels installed via `uv pip install --target`
3. Backend application package (with Alembic migrations)
4. Built frontend assets from `pnpm build`
5. Lightweight platform launcher scripts
"""

import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
DIST_DIR = REPO_ROOT / "dist"
CACHE_DIR = Path.home() / ".cache" / "workutil-packaging"


@dataclass(frozen=True)
class PackageTarget:
    name: str
    python_platform: str
    standalone_url: str
    expected_size: int
    expected_sha256: str
    launcher_filename: str
    launcher_content: str
    launcher_executable: bool


TARGETS: tuple[PackageTarget, ...] = (
    PackageTarget(
        name="windows-x64",
        python_platform="windows",
        standalone_url=(
            "https://github.com/astral-sh/python-build-standalone/releases/download/"
            "20260901/cpython-3.12.14%2B20260901-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
        ),
        expected_size=21980728,
        expected_sha256="7c45c9622400d578709a9b2cddbe8124cc21d382409d9f13406d706d28e31b14",
        launcher_filename="workutil.bat",
        launcher_content=(
            "@echo off\r\n"
            'set "PYTHONPATH=%~dp0site-packages;%~dp0."\r\n'
            'set "WORKUTIL_OPEN_WINDOW=1"\r\n'
            '"%~dp0python\\python.exe" -m app %*\r\n'
        ),
        launcher_executable=False,
    ),
    PackageTarget(
        name="macos-arm64",
        python_platform="macos",
        standalone_url=(
            "https://github.com/astral-sh/python-build-standalone/releases/download/"
            "20260901/cpython-3.12.14%2B20260901-aarch64-apple-darwin-install_only_stripped.tar.gz"
        ),
        expected_size=24981445,
        expected_sha256="81a359f1cfadd4da11766534c5913791cea55f26e1bb902cacd2a531bb1e4b2b",
        launcher_filename="workutil.command",
        launcher_content=(
            "#!/bin/sh\n"
            'DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'export PYTHONPATH="$DIR/site-packages:$DIR"\n'
            "export WORKUTIL_OPEN_WINDOW=1\n"
            'exec "$DIR/python/bin/python3" -m app "$@"\n'
        ),
        launcher_executable=True,
    ),
)

README_CONTENT = (
    "workutil - 本地工作辅助工具\r\n\r\n"
    "启动方式:\r\n"
    "- Windows: 双击 workutil.bat\r\n"
    "- macOS: 双击 workutil.command\r\n\r\n"
    "数据保存在系统应用数据目录 (%LOCALAPPDATA% / ~/Library/Application Support)。\r\n"
    "升级时只需解压新版本覆盖原文件夹，历史数据不会丢失。\r\n"
)


def get_project_version() -> str:
    pyproject = BACKEND_DIR / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    version = data.get("project", {}).get("version")
    if not version:
        raise ValueError(f"Version not found in {pyproject}")
    return str(version)


def build_frontend() -> None:
    print("Building frontend (pnpm build)...")
    res = subprocess.run(["pnpm", "--dir", str(FRONTEND_DIR), "build"], check=False)
    if res.returncode != 0:
        raise RuntimeError("Frontend build failed")


def fetch_standalone_python(target: PackageTarget) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    archive_name = target.standalone_url.split("/")[-1].replace("%2B", "+")
    cached_path = CACHE_DIR / archive_name

    def is_valid(path: Path) -> bool:
        if not path.is_file():
            return False
        if path.stat().st_size != target.expected_size:
            return False
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest() == target.expected_sha256

    if is_valid(cached_path):
        print(f"Using cached standalone Python for {target.name}: {cached_path.name}")
        return cached_path

    print(
        f"Downloading standalone Python for {target.name} from "
        f"{target.standalone_url}..."
    )
    temp_download = CACHE_DIR / f"{archive_name}.tmp"
    try:
        with (
            urllib.request.urlopen(target.standalone_url) as response,
            open(temp_download, "wb") as out_file,
        ):
            shutil.copyfileobj(response, out_file)
        if not is_valid(temp_download):
            raise RuntimeError(
                "Checksum or size verification failed for standalone Python: "
                f"{archive_name}"
            )
        temp_download.replace(cached_path)
    finally:
        if temp_download.exists():
            temp_download.unlink()

    return cached_path


def assemble_bundle(target: PackageTarget, version: str, python_tarball: Path) -> Path:
    print(f"\n--- Assembling bundle for {target.name} (v{version}) ---")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    output_zip = DIST_DIR / f"workutil-{version}-{target.name}.zip"

    with tempfile.TemporaryDirectory(prefix=f"workutil-{target.name}-") as tmp_str:
        tmp_dir = Path(tmp_str)
        bundle_root = tmp_dir / "workutil"
        bundle_root.mkdir()

        # 1. Unpack python runtime into workutil/python/
        print("Extracting Python runtime...")
        with tarfile.open(python_tarball, "r:gz") as tar:
            tar.extractall(path=bundle_root)

        python_dir = bundle_root / "python"
        if not python_dir.is_dir():
            raise RuntimeError(
                "Python runtime extraction did not produce a python/ directory"
            )

        # 2. Resolve dependencies with uv pip compile
        print(f"Compiling dependencies for platform={target.python_platform}...")
        reqs_file = tmp_dir / "requirements.txt"
        compile_cmd = [
            "uv",
            "pip",
            "compile",
            str(BACKEND_DIR / "pyproject.toml"),
            "--python-platform",
            target.python_platform,
            "--python-version",
            "3.12",
            "-o",
            str(reqs_file),
        ]
        res_compile = subprocess.run(compile_cmd, check=False)
        if res_compile.returncode != 0:
            raise RuntimeError(
                f"uv pip compile failed for platform {target.python_platform}"
            )

        # 3. Install precompiled wheels into site-packages/
        print(
            f"Installing precompiled wheels into site-packages for "
            f"{target.python_platform}..."
        )
        site_packages_dir = bundle_root / "site-packages"
        install_cmd = [
            "uv",
            "pip",
            "install",
            "-r",
            str(reqs_file),
            "--target",
            str(site_packages_dir),
            "--python-platform",
            target.python_platform,
            "--python-version",
            "3.12",
        ]
        res_install = subprocess.run(install_cmd, check=False)
        if res_install.returncode != 0:
            raise RuntimeError(
                f"uv pip install failed for platform {target.python_platform}"
            )

        # 4. Copy backend app/
        print("Copying app/ package and migrations...")
        target_app_dir = bundle_root / "app"
        shutil.copytree(
            BACKEND_DIR / "app",
            target_app_dir,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        migrations_versions = target_app_dir / "migrations" / "versions"
        if not migrations_versions.is_dir() or not any(
            migrations_versions.glob("*.py")
        ):
            raise RuntimeError(
                "Alembic migrations were not copied into app/migrations/versions"
            )

        # 5. Copy frontend dist/ to ui/
        print("Copying frontend dist/ to ui/...")
        frontend_dist = FRONTEND_DIR / "dist"
        if not (frontend_dist / "index.html").is_file():
            raise RuntimeError(
                "frontend/dist/index.html is missing; run pnpm build first"
            )
        shutil.copytree(frontend_dist, bundle_root / "ui")

        # 6. Write launcher script
        launcher_file = bundle_root / target.launcher_filename
        launcher_file.write_text(target.launcher_content, encoding="utf-8")
        if target.launcher_executable:
            launcher_file.chmod(0o755)

        # 7. Write README.txt
        (bundle_root / "README.txt").write_text(README_CONTENT, encoding="utf-8")

        # 8. Create zip archive preserving executable bits
        print(f"Archiving into {output_zip.name}...")
        if output_zip.exists():
            output_zip.unlink()

        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(bundle_root):
                rel_root = Path(root).relative_to(tmp_dir)
                for f in files:
                    file_path = Path(root) / f
                    arcname = str(rel_root / f)
                    info = zipfile.ZipInfo(arcname)
                    # `ZipFile.writestr` only picks up the ZipFile's own
                    # `compression=` default when given a plain arcname
                    # string; handing it a ZipInfo we built ourselves (as we
                    # must, to carry the executable bit below) means we own
                    # setting this too, or every entry is written ZIP_STORED
                    # and the "37MB" size in spec.md silently doubles.
                    info.compress_type = zipfile.ZIP_DEFLATED
                    st = file_path.stat()
                    if target.launcher_executable and f == target.launcher_filename:
                        info.external_attr = 0o100755 << 16
                    else:
                        info.external_attr = (st.st_mode & 0xFFFF) << 16
                    with open(file_path, "rb") as src:
                        zf.writestr(info, src.read())

    print(f"Created {output_zip} ({output_zip.stat().st_size // 1024 // 1024} MB)")
    return output_zip


def verify_packages(version: str) -> None:
    print("\n--- Verifying built packages ---")
    windows_zip = DIST_DIR / f"workutil-{version}-windows-x64.zip"
    macos_zip = DIST_DIR / f"workutil-{version}-macos-arm64.zip"

    if not windows_zip.is_file():
        raise FileNotFoundError(f"Missing Windows zip: {windows_zip}")
    if not macos_zip.is_file():
        raise FileNotFoundError(f"Missing macOS zip: {macos_zip}")

    # Inspect Windows package
    with zipfile.ZipFile(windows_zip, "r") as zf:
        names = set(zf.namelist())
        required_windows_entries = [
            "workutil/app/__init__.py",
            "workutil/ui/index.html",
            "workutil/site-packages/fastapi/__init__.py",
            "workutil/python/python.exe",
            "workutil/workutil.bat",
            "workutil/README.txt",
        ]
        for req in required_windows_entries:
            if req not in names:
                raise AssertionError(f"Windows zip missing required entry: {req}")

        migration_entries = [
            n
            for n in names
            if n.startswith("workutil/app/migrations/versions/") and n.endswith(".py")
        ]
        if not migration_entries:
            raise AssertionError(
                "Windows zip missing migration scripts in "
                "workutil/app/migrations/versions/"
            )

    print("Windows package contents verified successfully.")

    # Inspect macOS package
    with zipfile.ZipFile(macos_zip, "r") as zf:
        names = set(zf.namelist())
        required_macos_entries = [
            "workutil/app/__init__.py",
            "workutil/ui/index.html",
            "workutil/site-packages/fastapi/__init__.py",
            "workutil/python/bin/python3",
            "workutil/workutil.command",
            "workutil/README.txt",
        ]
        for req in required_macos_entries:
            if req not in names:
                raise AssertionError(f"macOS zip missing required entry: {req}")

        command_info = zf.getinfo("workutil/workutil.command")
        mode = command_info.external_attr >> 16
        if not (mode & 0o111):
            raise AssertionError(
                "workutil.command does not have executable bit set in zip"
            )

    print("macOS package contents verified successfully.")


def main() -> None:
    version = get_project_version()
    print(f"Building workutil portable packages v{version}...")

    # Build frontend
    build_frontend()

    # Build each target
    for target in TARGETS:
        python_tarball = fetch_standalone_python(target)
        assemble_bundle(target, version, python_tarball)

    # Verify packages
    verify_packages(version)
    print("\nAll packages built and verified successfully!")


if __name__ == "__main__":
    main()
