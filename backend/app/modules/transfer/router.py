import shutil

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse

from app.core.deps import SettingsDep
from app.modules.transfer import service

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
