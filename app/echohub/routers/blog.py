from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from core.config import templates
from database import get_db
from dependencies.auth import require_normal_user
from models.user import User
from utils.file_upload import save_file, IMAGE_DIR, VIDEO_DIR, FileUploadError
from fastapi.responses import RedirectResponse
from models.blogs import Blog
from utils.flash import flash
from echohub.services.notification_service import notify_mentions
from echohub.services.post_service import (
    parse_schedule,
    post_content_error,
    sync_tags,
)

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
    location: str | None = Form(None),
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    action: str = Form("publish"),
    scheduled_at: str | None = Form(None),
    tz_offset: int | None = Form(None),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    image_path = None
    video_path = None
    has_image = bool(image and image.filename)
    has_video = bool(video and video.filename)
    form_url = "/create-blog"

    content = content.strip()

    error = post_content_error(content)
    if error:
        flash(request, error, "danger")
        return RedirectResponse(
            url=form_url,
            status_code=303,
        )

    is_draft = action == "draft"
    publish_at, schedule_error = (None, None)
    if not is_draft:
        publish_at, schedule_error = parse_schedule(scheduled_at, tz_offset)
    if schedule_error:
        flash(request, schedule_error, "danger")
        return RedirectResponse(url=form_url, status_code=303)

    if has_image and has_video:
        flash(request, "You can upload either an image or a video, not both.", "danger")

        return RedirectResponse(
            url=form_url,
            status_code=303,
        )

    location = location.strip() if location else None
    if location and len(location) > 100:
        flash(request, "Location information is too long.", "danger")
        return RedirectResponse(url=form_url, status_code=303)

    try:
        if has_image:
            image_path = save_file(image, IMAGE_DIR)

        if has_video:
            video_path = save_file(video, VIDEO_DIR)
    except FileUploadError as e:
        flash(request, str(e), "danger")
        return RedirectResponse(url=form_url, status_code=303)

    new_blog = Blog(
        user_id=current_user.id,
        content=content,
        image=image_path,
        video=video_path,
        location=location or None,
        is_draft=is_draft,
    )
    if publish_at:
        new_blog.published_at = publish_at

    session.add(new_blog)
    sync_tags(session, new_blog)
    session.flush()
    notify_mentions(session, current_user.id, content, new_blog)
    session.commit()
    session.refresh(new_blog)

    if is_draft:
        flash(request, "Draft saved.", "success")
        return RedirectResponse(url="/user-blogs?tab=drafts", status_code=303)
    if publish_at:
        flash(request, "Post scheduled.", "success")
        return RedirectResponse(url="/user-blogs?tab=scheduled", status_code=303)

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@router.post("/blog/{blog_id}/location")
def update_blog_location(
    blog_id: int,
    location: str = Form(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    blog = session.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Post not found.")
    if blog.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot edit this post.")

    location = location.strip()
    if not location or len(location) > 100:
        raise HTTPException(status_code=400, detail="Invalid location name.")

    blog.location = location
    session.commit()
    return {"success": True, "location": location}
