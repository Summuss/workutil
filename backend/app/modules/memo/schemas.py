from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImageUpload(BaseModel):
    id: str
    data: str
    filename: str = "image.png"


class MemoCreate(BaseModel):
    body: str
    images: list[ImageUpload] = []


class MemoUpdate(BaseModel):
    body: str
    images: list[ImageUpload] = []


class MemoRead(BaseModel):
    """A memo as the list and the editor see it.

    Carries no title — the first line is cut from the body when displayed.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    created_at: datetime
    updated_at: datetime
    image_count: int = 0
