from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.ordering import Move


class MoveRequest(BaseModel):
    to: Move


class BookmarkGroupCreate(BaseModel):
    name: str


class BookmarkGroupUpdate(BaseModel):
    name: str


class BookmarkCreate(BaseModel):
    name: str
    path: str
    group_id: int | None = None


class BookmarkUpdate(BaseModel):
    name: str | None = None
    path: str | None = None
    group_id: int | None = None


class BookmarkRead(BaseModel):
    """A bookmark as the list and editor see it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    path: str
    is_directory: bool
    group_id: int | None = None
    order: int
    created_at: datetime
    updated_at: datetime


class BookmarkGroupRead(BaseModel):
    """A bookmark group with its member bookmarks."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    order: int
    created_at: datetime
    updated_at: datetime
    bookmarks: list[BookmarkRead] = []


class BookmarkListResponse(BaseModel):
    """GET /api/bookmarks returns groups in order and loose bookmarks in order."""

    groups: list[BookmarkGroupRead]
    loose: list[BookmarkRead]
