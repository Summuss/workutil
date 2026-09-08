"""Pasted screenshots on their way to disk, and back out again.

Memo and Evidence both take screenshots out of the clipboard, and this chain —
decode, name, write, clean up, serve — is the whole of what they share. It is a
mechanism, not a domain model: the two concepts stay apart, and nothing here
knows which one it is working for (ADR-0001). What they do *not* share is above
this line and below it — memo rewrites placeholders in a body of Markdown and
never counts references; an evidence block names one file and deletes it.

Every function takes the directory it works in. What a directory *means* — one
memo, one evidence — belongs to the feature that owns it and stays there.

The one thing that is not optional for either of them is the security line in
`serve`: images are user bytes served from this app's own origin, and the app
can reach a backend that opens local files (design.md §6 F1).
"""

import base64
import binascii
import contextlib
import shutil
from collections.abc import Sequence
from pathlib import Path

from fastapi import HTTPException, status
from fastapi.responses import FileResponse
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

    code = "image.invalid_image"


class IncomingImage(BaseModel):
    """A screenshot on its way in, still only a data URL.

    The filename is the browser's, and only its extension survives: what a
    stored image is called is decided in `save`.
    """

    data: str
    filename: str = "image.png"


class ImageUpload(IncomingImage):
    """An incoming screenshot that some text is holding a place for.

    `id` is the token standing in for the image in that text; the server swaps
    it for the saved image's URL. Text and images arrive in one request, so an
    image is never on disk without the thing that names it (spec 图片).

    Evidence has no such token — an image block *is* one screenshot — so it
    sends the base model. That difference is the whole of what the two
    concepts do not share here (ADR-0001).
    """

    id: str


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


def discard_file(path: Path) -> None:
    """Throw one image away, tolerating a file that will not go.

    The single-file half of `discard`, for a caller that owns one image among
    others in the same directory rather than the directory itself. Same rule
    for the same reason: whatever named the file is already gone.
    """
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


def _decode(upload: IncomingImage) -> bytes:
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


def save(directory: Path, images: Sequence[IncomingImage]) -> list[str]:
    """Write these images into `directory`, and answer what each was named.

    All or nothing, in that order: every image is decoded before any of them is
    written, so a bad one fails the whole save rather than leaving half a
    paste on disk, and a write that fails part-way takes back what it wrote.

    Names are chosen against what the directory already holds, so a directory
    shared by several things — an evidence's cases, say — never collides.
    """
    if not images:
        return []

    decoded = [(image, _decode(image)) for image in images]

    is_new_dir = not directory.exists()
    directory.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    names: list[str] = []
    try:
        taken = {path.name for path in directory.iterdir() if path.is_file()}
        index = 1
        for image, raw in decoded:
            suffix = Path(image.filename).suffix.lower()
            if suffix not in IMAGE_EXTENSIONS:
                suffix = ".png"
            while f"img_{index}{suffix}" in taken:
                index += 1
            name = f"img_{index}{suffix}"
            taken.add(name)

            path = directory / name
            path.write_bytes(raw)
            written.append(path)
            names.append(name)
    except OSError:
        # Half the screenshots is worse than none: whatever would have named
        # them is about to be rolled back with the rest of the save.
        for path in written:
            path.unlink(missing_ok=True)
        if is_new_dir:
            shutil.rmtree(directory, ignore_errors=True)
        raise

    return names


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
    for upload, name in zip(wanted, save(directory, wanted), strict=True):
        body = body.replace(upload.id, f"{url_prefix}/{name}")
    return body


def serve(directory: Path, filename: str) -> FileResponse:
    """One stored image, by the name `save` gave it — or a 404.

    Both halves of the security line every image response has to hold are
    here, so neither Memo nor Evidence can be the one that forgets (design.md
    §6 F1): a name is a name and never a path out of the directory, and the
    bytes came from a paste, so the browser must not go looking for something
    more interesting in them and end up running a document from this app's own
    origin.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "image not found")

    # And then checked again by where it actually landed, because the rule
    # above is about characters and the filesystem is not. On Windows —
    # a target platform — `Path("dir") / "C:evil.png"` is drive-relative and
    # leaves the directory while carrying none of the characters above.
    directory = directory.resolve()
    path = (directory / filename).resolve()
    if not path.is_relative_to(directory) or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "image not found")

    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff"})
