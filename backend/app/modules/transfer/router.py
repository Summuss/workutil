import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import SettingsDep
from app.modules.transfer import service
from app.modules.transfer.schemas import ImportResponse

router = APIRouter(prefix="/transfer", tags=["transfer"])


@router.get("/export")
def export_data_package(
    settings: SettingsDep,
    background_tasks: BackgroundTasks,
) -> FileResponse:
    """Export the entire workutil data package (database snapshot, images, manifest)."""
    temp_dir, zip_path, filename = service.export_data_package(settings)
    background_tasks.add_task(shutil.rmtree, temp_dir, ignore_errors=True)
    return FileResponse(
        path=zip_path,
        filename=filename,
        media_type="application/zip",
    )


@router.post("/import", response_model=ImportResponse)
def import_data_package(
    settings: SettingsDep,
    file: UploadFile,
) -> ImportResponse:
    """Import a workutil data package through the four safety gates."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = Path(temp_file.name)

    try:
        backup_file, restart_required = service.import_data_package(settings, temp_path)
        return ImportResponse(
            restart_required=restart_required,
            backup_file=backup_file,
            message=(
                "Data package imported successfully. "
                "Please restart workutil to apply changes."
            ),
        )
    except service.TransferError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"code": e.code, "message": e.message},
        ) from e
    finally:
        if temp_path.exists():
            temp_path.unlink()
