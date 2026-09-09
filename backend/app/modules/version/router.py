from fastapi import APIRouter
from pydantic import BaseModel

from app.core.version import get_version

router = APIRouter(tags=["version"])


class VersionResponse(BaseModel):
    version: str


@router.get("/version", response_model=VersionResponse)
def get_version_endpoint() -> VersionResponse:
    return VersionResponse(version=get_version())
