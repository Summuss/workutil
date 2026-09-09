"""HTTP for the app's own version.

Forwarding only — the behaviour lives in service.py.
"""

from fastapi import APIRouter

from app.modules.version import service
from app.modules.version.schemas import VersionResponse

router = APIRouter(tags=["version"])


@router.get("/version", response_model=VersionResponse)
def get_version_endpoint() -> VersionResponse:
    return VersionResponse(version=service.get_version())
