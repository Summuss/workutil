"""Pasted screenshots on their way to disk, and the URLs that point back.

Memo and Evidence both take screenshots out of the clipboard, and this chain —
decode everything, write it, rewrite the placeholders in the text — is the
whole of what they share. It is a mechanism, not a domain model: the two
concepts stay apart, and nothing here knows which one it is working for
(ADR-0001).

Every function takes the directory it works in. What a directory *means* — one
memo, one evidence — belongs to the feature that owns it and stays there.
"""

import base64
import binascii
import shutil
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

#: What a screenshot may be saved as. SVG is deliberately absent: it is a
#: scriptable document, and it would be served from this app's own origin,
#: which is the chain design.md §6 F1 exists to cut. Anything else is stored
#: as .png — the bytes are untouched either way, only the name is decided here.
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})

#: A screenshot is big; 25 MB of it is a mistake. The text and every image
#: travel in one request, so this bounds that request too.
MAX_IMAGE_BYTES = 25 * 1024 * 1024


class InvalidImage(ValueError):
    """Image data is malformed, unreadable, or too large."""


class ImageUpload(BaseModel):
    """A screenshot on its way in, still only a data URL and a placeholder.

    `id` is the token standing in for the image in the text; the server swaps
    it for the saved image's URL. Text and images arrive in one request, so an
    image is never on disk without the thing that names it (spec 图片).
    """

    id: str
    data: str
    filename: str = "image.png"


def count(directory: Path) -> int:
    """How many image files are in this directory.

    Derived from the directory rather than stored, so the files are the single
    truth and nothing can drift out of sync with them. The cost is that a
    directory left behind by a reused id would be counted as the newcomer's:
    clearing that is the caller's job, at the moment it hands out the id.
    """
    if not directory.is_dir():
        return 0
    return sum(1 for path in directory.iterdir() if path.is_file())


def discard(directory: Path) -> None:
    """Throw these images away, tolerating a file that will not go.

    On Windows a screenshot open in a viewer cannot be unlinked. That must not
    turn into a failed delete: whatever owned the images is already gone, and a
    refusal would say otherwise. What is left behind is cleared out when the id
    comes round again.
    """
    if directory.is_dir():
        shutil.rmtree(directory, ignore_errors=True)


def _decode(upload: ImageUpload) -> bytes:
    """The bytes behind a data URL, or a refusal.

    Every image is decoded before any of them is written, so one bad image
    fails the whole save instead of leaving half of them on disk.
    """
    data = upload.data
    encoded = data.split(";base64,", 1)[1] if ";base64," in data else data
    try:
        raw = base64.b64decode("".join(encoded.split()), validate=True)
    except (binascii.Error, ValueError) as bad:
        raise InvalidImage(f"image {upload.filename} is not valid base64") from bad

    if len(raw) > MAX_IMAGE_BYTES:
        raise InvalidImage(
            f"image {upload.filename} is larger than "
            f"{MAX_IMAGE_BYTES // (1024 * 1024)} MB"
        )
    return raw


def save_and_link(
    directory: Path,
    url_prefix: str,
    body: str,
    uploads: Sequence[ImageUpload],
) -> str:
    """Put the images this body still refers to on disk, and point it at them.

    An image whose placeholder was deleted while writing is not saved: the text
    decides what is being kept, right up to the moment it is sent.

    Returns the body with every placeholder replaced by `url_prefix` and the
    saved file's name, so `url_prefix` carries no trailing slash.
    """
    wanted = [upload for upload in uploads if upload.id in body]
    if not wanted:
        return body

    decoded = [(upload, _decode(upload)) for upload in wanted]

    is_new_dir = not directory.exists()
    directory.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    try:
        taken = {path.name for path in directory.iterdir() if path.is_file()}
        index = 1
        for upload, raw in decoded:
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in IMAGE_EXTENSIONS:
                suffix = ".png"
            while f"img_{index}{suffix}" in taken:
                index += 1
            name = f"img_{index}{suffix}"
            taken.add(name)

            path = directory / name
            path.write_bytes(raw)
            written.append(path)
            body = body.replace(upload.id, f"{url_prefix}/{name}")
    except OSError:
        # Half the screenshots is worse than none: the text that would have
        # named them is about to be rolled back with the rest of the save.
        for path in written:
            path.unlink(missing_ok=True)
        if is_new_dir:
            shutil.rmtree(directory, ignore_errors=True)
        raise

    return body
