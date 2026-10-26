from datetime import datetime

from fastapi import APIRouter, Request, Depends, status, File, UploadFile, Form, Query
from core.config import templates
from dependencies.auth import require_normal_user, require_normal_user_api
from models.user import User
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, or_, and_
from sqlalchemy.exc import IntegrityError
from database import get_db
from schemas.dependencies import update_profile_form
from schemas.auth import UpdateUserProfile
from fastapi.responses import RedirectResponse, JSONResponse
from models import Blog, Block, Follow, FollowRequest, Mute
from echohub.services.feed_service import (
    can_view_profile_content,
    is_blocked_between,
    newest_first,
    visible_blogs_query,
)
from echohub.services.social_service import (
    annotate_blogs,
    can_be_followed,
    follow_counts,
    has_requested_follow,
    is_following,
    requested_ids,
)
from echohub.services.notification_service import (
    notify_follow,
    notify_follow_request,
    notify_mentions,
)
from echohub.services.post_service import post_content_error, sync_tags
from utils.text import extract_mentions
from utils.file_upload import (
    save_file,
    delete_file,
    IMAGE_DIR,
    VIDEO_DIR,
    FileUploadError,
)
from utils.flash import flash
from utils.pagination import Page, paginate

router = APIRouter()

PROFILE_TABS = ("posts", "drafts", "scheduled")

# max lengths match the User model columns
PROFILE_FIELD_LIMITS = {"username": 50, "full_name": 50, "bio": 150}

POSTS_PAGE_SIZE = 10
FOLLOW_PAGE_SIZE = 20


def own_posts_query(user_id: int, tab: str):
    now = datetime.utcnow()
    query = select(Blog).where(Blog.user_id == user_id, Blog.is_hidden.is_(False))
    if tab == "drafts":
        query = query.where(Blog.is_draft.is_(True))
    elif tab == "scheduled":
        query = query.where(Blog.is_draft.is_(False), Blog.published_at > now)
    else:
        query = query.where(Blog.is_draft.is_(False), Blog.published_at <= now)
    return query.options(selectinload(Blog.repost_of).selectinload(Blog.user))


def published_post_count(session: Session, user_id: int):
    query = own_posts_query(user_id, "posts")
    return session.scalar(select(func.count()).select_from(query.subquery()))


def safe_next(next_url: str | None, fallback: str):
    # only same-site paths, so the form can't redirect off EchoHub
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return fallback


@router.get("/user-profile")
def user_profile_page(
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    post_count = published_post_count(session, current_user.id)
    follower_count, following_count = follow_counts(session, current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="/user/user_profile.html",
        context={
            "user": current_user,
            "post_count": post_count,
            "follower_count": follower_count,
            "following_count": following_count,
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
    page: int = Query(1, ge=1),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    if tab not in PROFILE_TABS:
        tab = "posts"
    pagination = paginate(
        session,
        newest_first(own_posts_query(current_user.id, tab)),
        page,
        POSTS_PAGE_SIZE,
    )
    blogs = pagination.items
    post_count = published_post_count(session, current_user.id)
    follower_count, following_count = follow_counts(session, current_user.id)
    return templates.TemplateResponse(
        request=request,
        name="/user/user_profile.html",
        context={
            "user": current_user,
            "blogs": blogs,
            "pagination": pagination,
            "post_count": post_count,
            "follower_count": follower_count,
            "following_count": following_count,
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

    if not blog or blog.user_id != current_user.id or blog.is_plain_repost:
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

    if not blog or blog.user_id != current_user.id or blog.is_plain_repost:
        return RedirectResponse(
            url="/user-blogs",
            status_code=303,
        )

    content = content.strip()
    error = post_content_error(content)
    if error:
        flash(request, error, "danger")
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

    # only people newly mentioned by the edit get notified
    already_mentioned = extract_mentions(blog.content)
    blog.content = content
    sync_tags(session, blog)
    new_mentions = extract_mentions(content) - already_mentioned
    if new_mentions:
        notify_mentions(
            session, current_user.id, " ".join(f"@{u}" for u in new_mentions), blog
        )

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


@router.post("/user-blog/{blog_id}/publish")
def publish_blog(
    request: Request,
    blog_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    """Publish a draft or a scheduled post right away."""
    blog = session.get(Blog, blog_id)
    if not blog or blog.user_id != current_user.id:
        return RedirectResponse(url="/user-blogs", status_code=303)

    was_draft = blog.is_draft
    blog.is_draft = False
    blog.published_at = datetime.utcnow()

    # drafts never notified anyone; scheduled posts did, timed for going live
    if was_draft:
        notify_mentions(session, current_user.id, blog.content, blog)
    else:
        for notification in blog.notifications:
            notification.created_at = blog.published_at
    session.commit()

    flash(request, "Post published.", "success")
    return RedirectResponse(url="/user-blogs", status_code=303)


def get_visible_profile(session: Session, username: str, viewer: User | None = None):
    profile_user = session.scalar(select(User).where(User.username == username))
    if not can_be_followed(profile_user):
        return None
    # someone who blocked you looks like they don't exist
    blocked_by_profile = viewer and session.scalar(
        select(Block.id).where(
            Block.blocker_id == profile_user.id, Block.blocked_id == viewer.id
        )
    )
    return None if blocked_by_profile else profile_user


def empty_page(page_size: int):
    return Page(items=[], page=1, per_page=page_size, total=0)


@router.get("/profile/{username}")
def public_profile(
    request: Request,
    username: str,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_db),
):
    current_user = request.state.user
    profile_user = get_visible_profile(session, username, current_user)

    if not profile_user:
        flash(request, "User not found.", "warning")
        return RedirectResponse(url="/", status_code=303)

    if current_user and current_user.id == profile_user.id:
        return RedirectResponse(url="/user-blogs", status_code=303)

    is_blocked = bool(current_user) and is_blocked_between(
        session, current_user.id, profile_user.id
    )
    is_muted = bool(current_user) and (
        session.scalar(
            select(Mute.id).where(
                Mute.muter_id == current_user.id, Mute.muted_id == profile_user.id
            )
        )
        is not None
    )
    can_view = not is_blocked and can_view_profile_content(
        session, current_user, profile_user
    )

    if can_view:
        pagination = paginate(
            session,
            newest_first(
                visible_blogs_query(current_user, include_muted=True).where(
                    Blog.user_id == profile_user.id
                )
            ),
            page,
            POSTS_PAGE_SIZE,
        )
    else:
        pagination = empty_page(POSTS_PAGE_SIZE)
    blogs = pagination.items
    annotate_blogs(session, blogs, current_user)
    follower_count, following_count = follow_counts(session, profile_user.id)

    return templates.TemplateResponse(
        request=request,
        name="/user/public_profile.html",
        context={
            "profile_user": profile_user,
            "current_user": current_user,
            "blogs": blogs,
            "pagination": pagination,
            "post_count": published_post_count(session, profile_user.id),
            "follower_count": follower_count,
            "following_count": following_count,
            "is_following": is_following(session, current_user, profile_user.id),
            "is_requested": has_requested_follow(
                session, current_user, profile_user.id
            ),
            "is_blocked": is_blocked,
            "is_muted": is_muted,
            "can_view": can_view,
            "flash": request.session.pop("_flash", None),
        },
    )


@router.get("/profile/{username}/{relation}")
def follow_list(
    request: Request,
    username: str,
    relation: str,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_db),
):
    if relation not in ("followers", "following"):
        return RedirectResponse(url=f"/profile/{username}", status_code=303)

    current_user = request.state.user
    profile_user = get_visible_profile(session, username, current_user)
    if not profile_user:
        flash(request, "User not found.", "warning")
        return RedirectResponse(url="/", status_code=303)

    if not can_view_profile_content(session, current_user, profile_user):
        flash(request, "This account is private.", "warning")
        return RedirectResponse(url=f"/profile/{username}", status_code=303)

    if relation == "followers":
        query = (
            select(User)
            .join(Follow, Follow.follower_id == User.id)
            .where(Follow.followed_id == profile_user.id)
        )
    else:
        query = (
            select(User)
            .join(Follow, Follow.followed_id == User.id)
            .where(Follow.follower_id == profile_user.id)
        )
    pagination = paginate(
        session,
        query.where(User.is_deleted.is_(False)).order_by(
            Follow.created_at.desc(), Follow.id.desc()
        ),
        page,
        FOLLOW_PAGE_SIZE,
    )

    followed_ids = set()
    if current_user:
        followed_ids = set(
            session.scalars(
                select(Follow.followed_id).where(Follow.follower_id == current_user.id)
            ).all()
        )

    return templates.TemplateResponse(
        request=request,
        name="/user/follow_list.html",
        context={
            "profile_user": profile_user,
            "relation": relation,
            "users": pagination.items,
            "pagination": pagination,
            "current_user": current_user,
            "followed_ids": followed_ids,
            "requested_ids": requested_ids(session, current_user),
            "flash": request.session.pop("_flash", None),
        },
    )


@router.post("/user/{user_id}/follow")
def toggle_follow(
    user_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user_api),
):
    if user_id == current_user.id:
        return JSONResponse(
            {"success": False, "message": "You cannot follow yourself."},
            status_code=400,
        )

    target = session.get(User, user_id)
    if not can_be_followed(target):
        return JSONResponse(
            {"success": False, "message": "User not found"}, status_code=404
        )

    if is_blocked_between(session, current_user.id, user_id):
        return JSONResponse(
            {"success": False, "message": "You cannot follow this user."},
            status_code=403,
        )

    existing = session.scalar(
        select(Follow).where(
            Follow.follower_id == current_user.id, Follow.followed_id == user_id
        )
    )
    pending = session.scalar(
        select(FollowRequest).where(
            FollowRequest.requester_id == current_user.id,
            FollowRequest.target_id == user_id,
        )
    )

    following = requested = False
    if existing:
        session.delete(existing)
    elif pending:
        # clicking "Requested" cancels the request
        session.delete(pending)
    elif target.is_private:
        follow_request = FollowRequest(requester_id=current_user.id, target_id=user_id)
        session.add(follow_request)
        notify_follow_request(session, follow_request)
        requested = True
    else:
        follow = Follow(follower_id=current_user.id, followed_id=user_id)
        session.add(follow)
        notify_follow(session, follow)
        following = True

    try:
        session.commit()
    except IntegrityError:
        # concurrent duplicate follow or request; it already exists
        session.rollback()
        following, requested = not target.is_private, target.is_private

    follower_count, _ = follow_counts(session, user_id)
    return JSONResponse(
        {
            "success": True,
            "following": following,
            "requested": requested,
            "follower_count": follower_count,
        }
    )


@router.post("/follow-requests/{request_id}/{decision}")
def answer_follow_request(
    request: Request,
    request_id: int,
    decision: str,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    follow_request = session.get(FollowRequest, request_id)
    if (
        decision not in ("approve", "decline")
        or not follow_request
        or follow_request.target_id != current_user.id
    ):
        return RedirectResponse(url="/notifications", status_code=303)

    if decision == "approve":
        approve_follow_request(session, follow_request)
        flash(request, "Follow request approved.", "success")
    else:
        flash(request, "Follow request declined.", "success")
    session.delete(follow_request)
    session.commit()
    return RedirectResponse(url="/notifications", status_code=303)


def approve_follow_request(session: Session, follow_request: FollowRequest):
    already_following = session.scalar(
        select(Follow.id).where(
            Follow.follower_id == follow_request.requester_id,
            Follow.followed_id == follow_request.target_id,
        )
    )
    if not already_following:
        session.add(
            Follow(
                follower_id=follow_request.requester_id,
                followed_id=follow_request.target_id,
            )
        )


def restrictable_user(session: Session, current_user: User, user_id: int):
    target = session.get(User, user_id)
    if not target or target.id == current_user.id or not can_be_followed(target):
        return None
    return target


@router.post("/user/{user_id}/block")
def toggle_block(
    request: Request,
    user_id: int,
    next: str | None = Form(None),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    target = restrictable_user(session, current_user, user_id)
    if not target:
        return RedirectResponse(url=safe_next(next, "/"), status_code=303)

    existing = session.scalar(
        select(Block).where(
            Block.blocker_id == current_user.id, Block.blocked_id == user_id
        )
    )
    if existing:
        session.delete(existing)
        flash(request, f"Unblocked @{target.username}.", "success")
    else:
        session.add(Block(blocker_id=current_user.id, blocked_id=user_id))
        # a block ends any follow relationship in both directions
        both_ways = or_(
            and_(Follow.follower_id == current_user.id, Follow.followed_id == user_id),
            and_(Follow.follower_id == user_id, Follow.followed_id == current_user.id),
        )
        requests_both_ways = or_(
            and_(
                FollowRequest.requester_id == current_user.id,
                FollowRequest.target_id == user_id,
            ),
            and_(
                FollowRequest.requester_id == user_id,
                FollowRequest.target_id == current_user.id,
            ),
        )
        # ORM deletes so their notifications go with them
        for row in [
            *session.scalars(select(Follow).where(both_ways)).all(),
            *session.scalars(select(FollowRequest).where(requests_both_ways)).all(),
        ]:
            session.delete(row)
        flash(request, f"Blocked @{target.username}.", "success")

    session.commit()
    return RedirectResponse(
        url=safe_next(next, f"/profile/{target.username}"), status_code=303
    )


@router.post("/user/{user_id}/mute")
def toggle_mute(
    request: Request,
    user_id: int,
    next: str | None = Form(None),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    target = restrictable_user(session, current_user, user_id)
    if not target:
        return RedirectResponse(url=safe_next(next, "/"), status_code=303)

    existing = session.scalar(
        select(Mute).where(Mute.muter_id == current_user.id, Mute.muted_id == user_id)
    )
    if existing:
        session.delete(existing)
        flash(request, f"Unmuted @{target.username}.", "success")
    else:
        session.add(Mute(muter_id=current_user.id, muted_id=user_id))
        flash(request, f"Muted @{target.username}.", "success")

    session.commit()
    return RedirectResponse(
        url=safe_next(next, f"/profile/{target.username}"), status_code=303
    )
