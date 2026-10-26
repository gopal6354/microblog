from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


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

CHUNK_SIZE = 1024 * 1024


class FileUploadError(ValueError):
    pass


def save_file(
    file: UploadFile,
    upload_dir: Path,
):
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS[upload_dir]:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS[upload_dir]))
        raise FileUploadError(f"Unsupported file type. Allowed types: {allowed}.")

    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"

    filepath = upload_dir / filename

    max_size = MAX_FILE_SIZE[upload_dir]
    written = 0

    with filepath.open("wb") as buffer:
        while chunk := file.file.read(CHUNK_SIZE):
            written += len(chunk)

            if written > max_size:
                buffer.close()
                filepath.unlink(missing_ok=True)
                raise FileUploadError(
                    f"File is too large. Maximum size is {max_size // (1024 * 1024)} MB."
                )

            buffer.write(chunk)

    return filepath.relative_to(STATIC_DIR).as_posix()


def delete_file(relative_path: str | None):
    if not relative_path:
        return

    filepath = (STATIC_DIR / relative_path).resolve()
    uploads_dir = (STATIC_DIR / "uploads").resolve()

    if uploads_dir in filepath.parents:
        filepath.unlink(missing_ok=True)
