from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.memo.models import Memo


class ImageUpload(BaseModel):
    """A screenshot on its way in, still only a data URL and a placeholder.

    `id` is the token standing in for the image in the body; the server swaps
    it for the saved image's URL. Body and images arrive in one request, so an
    image is never on disk without the memo that names it (spec 图片).
    """

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
    Images are counted, never sent: that is what keeps the list quick once a
    few hundred screenshots have piled up (spec 接口契约).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    created_at: datetime
    updated_at: datetime
    image_count: int = 0
    snippets: list[str] = []
    #: How many places matched, which can be more than `snippets` shows.
    snippet_total: int = 0

    @classmethod
    def of(
        cls,
        memo: Memo,
        image_count: int = 0,
        snippets: Sequence[str] = (),
        snippet_total: int = 0,
    ) -> "MemoRead":
        return cls(
            id=memo.id,
            body=memo.body,
            created_at=memo.created_at,
            updated_at=memo.updated_at,
            image_count=image_count,
            snippets=list(snippets),
            snippet_total=snippet_total,
        )
