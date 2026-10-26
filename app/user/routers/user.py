from fastapi import APIRouter, Request, Depends, status, File, UploadFile, Form
from core.config import templates
from dependencies.auth import require_normal_user
from models.user import User
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db
from schemas.dependencies import update_profile_form
from schemas.auth import UpdateUserProfile
from fastapi.responses import RedirectResponse
from models.blogs import Blog
from utils.file_upload import (
    save_file,
    delete_file,
    IMAGE_DIR,
    VIDEO_DIR,
    FileUploadError,
)
from utils.flash import flash

router = APIRouter()

# max lengths match the User model columns
PROFILE_FIELD_LIMITS = {"username": 50, "full_name": 50, "bio": 150}


@router.get("/user-profile")
def user_profile_page(
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    blogs = current_user.blogs
    post_count = len(blogs)

    # user = sesssion.scalars(select(User).where((User.username)))
    return templates.TemplateResponse(
        request=request,
        name="/user/user_profile.html",
        context={
            "user": current_user,
            "post_count": post_count,
            "flash": request.session.pop("_flash", None),
        },
    )


@router.get("/profile-edit")
def edit_profile_page(
    request: Request, current_user: User = Depends(require_normal_user)
):
    return templates.TemplateResponse(
        request=request,
        name="/user/update_user_profile.html",
        context={"user": current_user, "flash": request.session.pop("_flash", None)},
    )


@router.post("/profile-edit")
def edit_user_profile(
    request: Request,
    user: UpdateUserProfile = Depends(update_profile_form),
    session: Session = Depends(get_db),
    profile_image: UploadFile | None = File(None),
    current_user: User = Depends(require_normal_user),
):
    data = user.model_dump(exclude_unset=True)

    if "username" in data:
        data["username"] = data["username"].strip()

        if not data["username"]:
            flash(request, "Username cannot be empty.", "danger")
            return RedirectResponse(url="/profile-edit", status_code=303)

        username_taken = session.scalar(
            select(User).where(
                User.username == data["username"], User.id != current_user.id
            )
        )
        if username_taken:
            flash(request, "This username is already taken.", "danger")
            return RedirectResponse(url="/profile-edit", status_code=303)

    for field, limit in PROFILE_FIELD_LIMITS.items():
        if data.get(field) and len(data[field]) > limit:
            label = field.replace("_", " ").capitalize()
            flash(request, f"{label} cannot exceed {limit} characters.", "danger")
            return RedirectResponse(url="/profile-edit", status_code=303)

    old_profile_image = None
    if profile_image and profile_image.filename:
        try:
            new_profile_image = save_file(profile_image, IMAGE_DIR)
        except FileUploadError as e:
            flash(request, str(e), "danger")
            return RedirectResponse(url="/profile-edit", status_code=303)

        old_profile_image = current_user.profile_image
        current_user.profile_image = new_profile_image

    for k, val in data.items():
        setattr(current_user, k, val)

    session.commit()
    delete_file(old_profile_image)
    session.refresh(current_user)
    return RedirectResponse(url="/user-profile", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/user-blogs")
def user_blogs(
    request: Request,
    tab: str = "posts",
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    blogs = session.scalars(
        select(Blog)
        .where(Blog.user_id == current_user.id, Blog.is_hidden.is_(False))
        .order_by(Blog.created_at.desc())
    ).all()
    post_count = len(blogs)
    return templates.TemplateResponse(
        request=request,
        name="/user/user_profile.html",
        context={
            "user": current_user,
            "blogs": blogs,
            "post_count": post_count,
            "active_tab": tab,
            "flash": request.session.pop("_flash", None),
        },
    )


@router.post("/user-blog/{blog_id}/delete")
def delete_blog(
    blog_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    blog = session.get(Blog, blog_id)

    if blog and blog.user_id == current_user.id:
        media = [blog.image, blog.video]
        session.delete(blog)
        session.commit()

        for path in media:
            delete_file(path)

    return RedirectResponse(
        url="/user-blogs",
        status_code=303,
    )


@router.get("/user-blog/{blog_id}/edit")
def edit_blog_page(
    request: Request,
    blog_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    blog = session.get(Blog, blog_id)

    if not blog or blog.user_id != current_user.id:
        return RedirectResponse(
            url="/user-blogs",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="blog/blog.html",
        context={
            "user": current_user,
            "is_edit": True,
            "blog": blog,
            "flash": request.session.pop("_flash", None),
        },
    )


@router.post("/user-blog/{blog_id}/edit")
async def update_blog(
    request: Request,
    blog_id: int,
    content: str = Form(...),
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    blog = session.get(Blog, blog_id)

    if not blog or blog.user_id != current_user.id:
        return RedirectResponse(
            url="/user-blogs",
            status_code=303,
        )

    content = content.strip()
    if not content:
        flash(request, "Post content cannot be empty.", "danger")
        return RedirectResponse(
            url=f"/user-blog/{blog_id}/edit",
            status_code=303,
        )

    if len(content.split()) > 280:
        flash(request, "Your post cannot exceed 280 words.", "danger")
        return RedirectResponse(
            url=f"/user-blog/{blog_id}/edit",
            status_code=303,
        )

    has_image = bool(image and image.filename)
    has_video = bool(video and video.filename)

    if has_image and has_video:
        flash(
            request,
            "You can upload either an image or a video, not both.",
            "danger",
        )

        return RedirectResponse(
            url=f"/user-blog/{blog_id}/edit",
            status_code=303,
        )

    try:
        new_image = save_file(image, IMAGE_DIR) if has_image else None
        new_video = save_file(video, VIDEO_DIR) if has_video else None
    except FileUploadError as e:
        flash(request, str(e), "danger")
        return RedirectResponse(
            url=f"/user-blog/{blog_id}/edit",
            status_code=303,
        )

    blog.content = content

    # a post holds either an image or a video, so new media replaces both
    replaced_media = []
    if new_image or new_video:
        replaced_media = [blog.image, blog.video]
        blog.image = new_image
        blog.video = new_video

    session.commit()

    for path in replaced_media:
        delete_file(path)

    return RedirectResponse(
        url="/user-blogs",
        status_code=303,
    )
