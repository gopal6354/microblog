from fastapi import APIRouter, Request, Depends, Form, File, UploadFile
from sqlalchemy.orm import Session
from core.config import templates
from database import get_db
from dependencies.auth import require_normal_user
from models.user import User
from utils.file_upload import save_file, IMAGE_DIR, VIDEO_DIR
from fastapi.responses import RedirectResponse
from models.blogs import Blog
from utils.flash import flash

router = APIRouter()


@router.get("/create-blog")
def create_blog_page(
    request: Request,
    current_user: User = Depends(require_normal_user),
    session: Session = Depends(get_db),
):
    return templates.TemplateResponse(
        request=request,
        name="/blog/blog.html",
        context={
            "user": current_user,
            "is_edit": False,
            "blog": None,
            "flash": request.session.pop("_flash", None),
        },
    )


@router.post("/create-blog")
async def create_blog(
    request: Request,
    content: str = Form(...),
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    image_path = None
    video_path = None
    has_image = bool(image and image.filename)
    has_video = bool(video and video.filename)

    content = content.strip()

    if not content:
        flash(request, "Post content cannot be empty.", "danger")
        return RedirectResponse(
            url="/create-blog",
            status_code=303,
        )

    words = content.split()

    if len(words) > 280:
        flash(request, "Your post cannot exceed 150 words.", "danger")
        return RedirectResponse(
            url="/create-blog",
            status_code=303,
        )

    if has_image and has_video:
        flash(request, "You can upload either an image or a video, not both.", "danger")

        return RedirectResponse(
            url="/create-blog",
            status_code=303,
        )

    if has_image:
        image_path = save_file(image, IMAGE_DIR)

    if has_video:
        video_path = save_file(video, VIDEO_DIR)

    new_blog = Blog(
        user_id=current_user.id,
        content=content,
        image=image_path,
        video=video_path,
    )

    session.add(new_blog)
    session.commit()
    session.refresh(new_blog)

    return RedirectResponse(
        url="/",
        status_code=303,
    )
