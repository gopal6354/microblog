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
from utils.file_upload import save_file, IMAGE_DIR, VIDEO_DIR
from utils.flash import flash

router = APIRouter()


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
        context={"user": current_user, "post_count": post_count},
    )


@router.get("/profile-edit")
def edit_profile_page(
    request: Request, current_user: User = Depends(require_normal_user)
):
    return templates.TemplateResponse(
        request=request,
        name="/user/update_user_profile.html",
        context={"user": current_user},
    )


@router.post("/profile-edit")
def edit_user_profile(
    request: Request,
    user: UpdateUserProfile = Depends(update_profile_form),
    session: Session = Depends(get_db),
    profile_image: UploadFile | None = File(None),
    current_user: User = Depends(require_normal_user),
):
    for k, val in user.model_dump(exclude_unset=True).items():
        setattr(current_user, k, val)

    if profile_image and profile_image.filename:
        current_user.profile_image = save_file(profile_image, IMAGE_DIR)

    session.commit()
    print("data save")
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
        session.delete(blog)
        session.commit()

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

    blog.content = content

    if has_image:
        blog.image = save_file(image, IMAGE_DIR)

    if has_video:
        blog.video = save_file(video, VIDEO_DIR)

    session.commit()

    return RedirectResponse(
        url="/user-blogs",
        status_code=303,
    )
