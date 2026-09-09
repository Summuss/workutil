from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.ordering import Move
from app.core.ordering import MoveRequest as MoveRequest


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


class BookmarkMoveRequest(BaseModel):
    to: Move | int
    group_id: int | None = None


class BookmarkMoveResponse(BaseModel):
    source_group_id: int | None = None
    target_group_id: int | None = None
    source: list[BookmarkRead]
    target: list[BookmarkRead]


class BookmarkActionResponse(BaseModel):
    ok: bool = True
    id: int
    name: str
    path: str


class OpenedBookmark(BaseModel):
    id: int
    name: str
    path: str


class SkippedBookmark(BaseModel):
    id: int
    name: str
    path: str
    reason: str


class BookmarkGroupOpenResponse(BaseModel):
    opened: list[OpenedBookmark]
    skipped: list[SkippedBookmark]


class BookmarkCheckRequest(BaseModel):
    ids: list[int] | None = None


class BookmarkCheckItem(BaseModel):
    id: int
    exists: bool


class BookmarkCheckResponse(BaseModel):
    items: list[BookmarkCheckItem]
