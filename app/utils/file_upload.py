import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import cloudinary
import cloudinary.exceptions
import cloudinary.uploader
from fastapi import UploadFile
from jinja2 import pass_context

from core.config import settings


STATIC_DIR = Path("static")
IMAGE_DIR = STATIC_DIR / "uploads/images"
VIDEO_DIR = STATIC_DIR / "uploads/videos"

ALLOWED_EXTENSIONS = {
    IMAGE_DIR: {".jpg", ".jpeg", ".jfif", ".png", ".gif", ".webp"},
    VIDEO_DIR: {".mp4", ".mov", ".webm"},
}

MAX_FILE_SIZE = {
    IMAGE_DIR: 5 * 1024 * 1024,
    VIDEO_DIR: 50 * 1024 * 1024,
}

CLOUDINARY_RESOURCE_TYPE = {
    IMAGE_DIR: "image",
    VIDEO_DIR: "video",
}

CLOUDINARY_FOLDER = "microblog"

CHUNK_SIZE = 1024 * 1024

# https://res.cloudinary.com/<cloud>/<resource_type>/upload/v<version>/<public_id>.<ext>
CLOUDINARY_URL_PATTERN = re.compile(
    r"^https?://res\.cloudinary\.com/[^/]+/(?P<resource_type>image|video)/upload/"
    r"(?:v\d+/)?(?P<public_id>.+?)(?:\.[A-Za-z0-9]+)?$"
)


if settings.USE_CLOUDINARY:
    # cloudinary://<api_key>:<api_secret>@<cloud_name>
    _cloudinary_url = urlparse(settings.CLOUDINARY_URL)
    cloudinary.config(
        cloud_name=_cloudinary_url.hostname,
        api_key=_cloudinary_url.username,
        api_secret=_cloudinary_url.password,
        secure=True,
    )


class FileUploadError(ValueError):
    pass


def _copy_limited(file: UploadFile, buffer, max_size: int):
    written = 0

    while chunk := file.file.read(CHUNK_SIZE):
        written += len(chunk)

        if written > max_size:
            raise FileUploadError(
                f"File is too large. Maximum size is {max_size // (1024 * 1024)} MB."
            )

        buffer.write(chunk)


def save_file(
    file: UploadFile,
    upload_dir: Path,
):
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS[upload_dir]:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS[upload_dir]))
        raise FileUploadError(f"Unsupported file type. Allowed types: {allowed}.")

    max_size = MAX_FILE_SIZE[upload_dir]

    if settings.USE_CLOUDINARY:
        return _save_to_cloudinary(file, upload_dir, max_size)

    upload_dir.mkdir(parents=True, exist_ok=True)

    filepath = upload_dir / f"{uuid4().hex}{extension}"

    try:
        with filepath.open("wb") as buffer:
            _copy_limited(file, buffer, max_size)
    except FileUploadError:
        filepath.unlink(missing_ok=True)
        raise

    return filepath.relative_to(STATIC_DIR).as_posix()


def _save_to_cloudinary(file: UploadFile, upload_dir: Path, max_size: int):
    resource_type = CLOUDINARY_RESOURCE_TYPE[upload_dir]

    # check the size before sending anything to cloudinary
    with tempfile.SpooledTemporaryFile(max_size=CHUNK_SIZE * 5) as buffer:
        _copy_limited(file, buffer, max_size)
        buffer.seek(0)

        try:
            result = cloudinary.uploader.upload(
                buffer,
                public_id=uuid4().hex,
                folder=f"{CLOUDINARY_FOLDER}/{resource_type}s",
                resource_type=resource_type,
            )
        except cloudinary.exceptions.Error as exc:
            raise FileUploadError(
                "Could not upload the file. Please try again."
            ) from exc

    return result["secure_url"]


def delete_file(path: str | None):
    if not path:
        return

    if path.startswith(("http://", "https://")):
        _delete_from_cloudinary(path)
        return

    filepath = (STATIC_DIR / path).resolve()
    uploads_dir = (STATIC_DIR / "uploads").resolve()

    if uploads_dir in filepath.parents:
        filepath.unlink(missing_ok=True)


def _delete_from_cloudinary(url: str):
    match = CLOUDINARY_URL_PATTERN.match(url)

    if not match or not settings.USE_CLOUDINARY:
        return

    try:
        cloudinary.uploader.destroy(
            match["public_id"],
            resource_type=match["resource_type"],
            invalidate=True,
        )
    except cloudinary.exceptions.Error:
        # the database row is already gone, a leftover remote file is not fatal
        pass


@pass_context
def media_url(context, path: str):
    # cloudinary uploads are stored as full urls, local uploads as static paths
    if path.startswith(("http://", "https://")):
        return path

    return context["request"].url_for("static", path=path)
