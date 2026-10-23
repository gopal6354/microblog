from pathlib import Path
from uuid import uuid4
import shutil

from fastapi import UploadFile


IMAGE_DIR = Path("static/uploads/images")
VIDEO_DIR = Path("static/uploads/videos")


def save_file(
    file: UploadFile,
    upload_dir: Path,
):
    extension = Path(file.filename).suffix

    filename = f"{uuid4().hex}{extension}"

    filepath = upload_dir / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(filepath).replace("static/", "")
