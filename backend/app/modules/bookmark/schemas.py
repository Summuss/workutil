from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookmarkCreate(BaseModel):
    name: str
    path: str


class BookmarkUpdate(BaseModel):
    name: str | None = None
    path: str | None = None


class BookmarkRead(BaseModel):
    """A bookmark as the list and editor see it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    path: str
    is_directory: bool
    created_at: datetime
    updated_at: datetime
