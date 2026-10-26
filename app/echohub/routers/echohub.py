from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, or_
from database import get_db
from models import Blog, User, Like, Report, Comment, Bookmark, Follow
from models.report import ReportReason
from core.config import templates
from dependencies.auth import require_normal_user, require_normal_user_api
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from echohub.services.feed_service import (
    FEED_PAGE_SIZE,
    can_view_blog,
    is_blocked_between,
    newest_first,
    visible_blogs_query,
)
from echohub.services.social_service import (
    MAX_COMMENT_LENGTH,
    annotate_blogs,
    suggested_users,
    visible_comment_count,
)
from echohub.services.notification_service import (
    notify_comment,
    notify_mentions,
    notify_reply,
    notify_repost,
)
from utils.flash import flash
from utils.pagination import paginate

router = APIRouter()


def comment_error(content: str):
    if not content:
        return "Comment cannot be empty."
    if len(content) > MAX_COMMENT_LENGTH:
        return f"Comment cannot exceed {MAX_COMMENT_LENGTH} characters."
    return None


def error_response(message: str, status_code: int):
    return JSONResponse({"success": False, "message": message}, status_code=status_code)


# Home feed: 'for-you' shows all visible posts.
# 'following' shows only your own posts and those of people you follow.
@router.get("/")
def blogs(
    request: Request,
    feed: str = "for-you",
    page: int = Query(1, ge=1),
    session: Session = Depends(get_db),
):
    current_user = request.state.user
    query = visible_blogs_query(current_user)

    # the following feed is your own posts plus those of people you follow
    if feed == "following" and current_user:
        followed_ids = select(Follow.followed_id).where(
            Follow.follower_id == current_user.id
        )
        query = query.where(
            or_(Blog.user_id == current_user.id, Blog.user_id.in_(followed_ids))
        )
    else:
        feed = "for-you"

    pagination = paginate(session, newest_first(query), page, FEED_PAGE_SIZE)
    blogs = pagination.items
    annotate_blogs(session, blogs, current_user)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "blogs": blogs,
            "pagination": pagination,
            "feed": feed,
            "current_user": current_user,
            "suggested_users": suggested_users(session, current_user),
            "flash": request.session.pop("_flash", None),
        },
    )


# Shows a single post with its comments.
# Redirects home if the post is hidden, private or blocked for this viewer.
@router.get("/post/{blog_id}")
def post_detail(request: Request, blog_id: int, session: Session = Depends(get_db)):
    current_user = request.state.user
    blog = session.scalars(
        visible_blogs_query(current_user, include_muted=True).where(Blog.id == blog_id)
    ).first()

    if not blog:
        flash(request, "This post is unavailable.", "warning")
        return RedirectResponse(url="/", status_code=303)

    annotate_blogs(session, [blog], current_user)

    return templates.TemplateResponse(
        request=request,
        name="blog/post_detail.html",
        context={
            "blog": blog,
            "current_user": current_user,
            "suggested_users": suggested_users(session, current_user),
            "flash": request.session.pop("_flash", None),
        },
    )


# JSON API: toggles a like on a post.
# Returns the new liked state and the updated like count.
@router.post("/blog/{blog_id}/like")
def like_blog(
    blog_id: int,
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user_api),
):
    if not current_user:
        return JSONResponse(
            {"success": False, "message": "Login required"}, status_code=401
        )

    blog = session.get(Blog, blog_id)
    if not can_view_blog(session, current_user, blog):
        return JSONResponse(
            {"success": False, "message": "Post not found"}, status_code=404
        )

    exits_like = session.scalar(
        select(Like).where(Like.user_id == current_user.id, Like.blog_id == blog_id)
    )

    if exits_like:
        session.delete(exits_like)
        liked = False
    else:
        new_like = Like(user_id=current_user.id, blog_id=blog_id)
        session.add(new_like)
        liked = True

    try:
        session.commit()
    except IntegrityError:
        # concurrent duplicate like; the like already exists
        session.rollback()
        liked = True
    like_count = session.scalar(
        select(func.count(Like.id)).where(Like.blog_id == blog_id)
    )

    return JSONResponse({"success": True, "liked": liked, "like_count": like_count})


# JSON API: adds a comment or a reply (parent_id) to a post.
# Notifies the owner, parent commenter and mentions; returns the rendered comment HTML.
@router.post("/blog/{blog_id}/comment")
def add_comment(
    blog_id: int,
    request: Request,
    content: str = Form(...),
    parent_id: int | None = Form(None),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user_api),
):
    blog = session.get(Blog, blog_id)
    if not can_view_blog(session, current_user, blog):
        return error_response("Post not found", 404)

    content = content.strip()
    error = comment_error(content)
    if error:
        return error_response(error, 400)

    parent = None
    if parent_id is not None:
        parent = session.get(Comment, parent_id)
        if not parent or parent.blog_id != blog_id:
            return error_response("Comment not found", 404)
        # keep threads one level deep
        if parent.parent_id:
            parent = parent.parent
        if is_blocked_between(session, current_user.id, parent.user_id):
            return error_response("You cannot reply to this comment.", 403)

    comment = Comment(
        user_id=current_user.id,
        blog_id=blog_id,
        content=content,
        parent_id=parent.id if parent else None,
    )
    session.add(comment)

    notified = set()
    if parent:
        notify_reply(session, parent, comment)
        notified.add(parent.user_id)
    if blog.user_id not in notified:
        notify_comment(session, blog, comment)
        notified.add(blog.user_id)
    notify_mentions(session, current_user.id, content, blog, comment, skip=notified)
    session.commit()
    session.refresh(comment)

    # render the same partial the feed uses so new comments look identical
    comment_html = templates.get_template("partials/comment_item.html").render(
        request=request, comment=comment, current_user=current_user
    )

    return JSONResponse(
        {
            "success": True,
            "comment_html": comment_html,
            "parent_id": comment.parent_id,
            "comment_count": visible_comment_count(session, blog_id),
        }
    )


# JSON API: edits the text of the user's own comment.
# Sets updated_at so the comment shows as edited.
@router.post("/comment/{comment_id}/edit")
def edit_comment(
    comment_id: int,
    content: str = Form(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user_api),
):
    comment = session.get(Comment, comment_id)
    if not comment:
        return error_response("Comment not found", 404)
    if current_user.id != comment.user_id:
        return error_response("You cannot edit this comment.", 403)

    content = content.strip()
    error = comment_error(content)
    if error:
        return error_response(error, 400)

    if content != comment.content:
        comment.content = content
        comment.updated_at = datetime.utcnow()
        session.commit()

    return JSONResponse(
        {
            "success": True,
            "content": comment.content,
            "edited": bool(comment.updated_at),
        }
    )


# JSON API: deletes the user's own comment.
# Returns the post's updated comment count.
@router.post("/comment/{comment_id}/delete")
def delete_comment(
    comment_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user_api),
):
    comment = session.get(Comment, comment_id)
    if not comment:
        return JSONResponse(
            {"success": False, "message": "Comment not found"}, status_code=404
        )

    # only the comment author can remove a comment
    if current_user.id != comment.user_id:
        return JSONResponse(
            {"success": False, "message": "You cannot delete this comment."},
            status_code=403,
        )

    blog_id = comment.blog_id
    session.delete(comment)
    session.commit()

    return JSONResponse(
        {"success": True, "comment_count": visible_comment_count(session, blog_id)}
    )


# JSON API: toggles a bookmark on a post.
# Returns the new bookmarked state.
@router.post("/blog/{blog_id}/bookmark")
def toggle_bookmark(
    blog_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user_api),
):
    blog = session.get(Blog, blog_id)
    if not can_view_blog(session, current_user, blog):
        return error_response("Post not found", 404)

    existing = session.scalar(
        select(Bookmark).where(
            Bookmark.user_id == current_user.id, Bookmark.blog_id == blog_id
        )
    )
    if existing:
        session.delete(existing)
        bookmarked = False
    else:
        session.add(Bookmark(user_id=current_user.id, blog_id=blog_id))
        bookmarked = True

    try:
        session.commit()
    except IntegrityError:
        # concurrent duplicate bookmark; the bookmark already exists
        session.rollback()
        bookmarked = True

    return JSONResponse({"success": True, "bookmarked": bookmarked})


def repost_target(session: Session, current_user: User, blog_id: int):
    """The post a repost would point at, or an error message and status."""
    blog = session.get(Blog, blog_id)
    if not can_view_blog(session, current_user, blog):
        return None, ("Post not found", 404)
    # reposting a plain repost reposts the original
    if blog.is_plain_repost:
        blog = blog.repost_of
    if blog.user.is_private:
        return None, ("Posts from private accounts can't be reposted.", 403)
    return blog, None


# JSON API: toggles a plain repost of a post.
# You can't repost your own posts or posts from private accounts.
@router.post("/blog/{blog_id}/repost")
def toggle_repost(
    blog_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user_api),
):
    original, error = repost_target(session, current_user, blog_id)
    if error:
        return error_response(*error)
    if original.user_id == current_user.id:
        return error_response("You cannot repost your own post.", 400)

    existing = session.scalar(
        select(Blog).where(
            Blog.user_id == current_user.id,
            Blog.repost_of_id == original.id,
            Blog.content == "",
        )
    )
    if existing:
        session.delete(existing)
        reposted = False
    else:
        repost = Blog(user_id=current_user.id, content="", repost_of_id=original.id)
        session.add(repost)
        notify_repost(session, original, repost)
        reposted = True
    session.commit()

    repost_count = session.scalar(
        select(func.count(Blog.id)).where(
            Blog.repost_of_id == original.id, Blog.is_hidden.is_(False)
        )
    )
    return JSONResponse(
        {"success": True, "reposted": reposted, "repost_count": repost_count}
    )


# Saves a user's report about a post (reason and optional description).
# Each user can report a post only once, and not their own posts.
@router.post("/report/blog")
def report_blog(
    request: Request,
    session: Session = Depends(get_db),
    blog_id: int = Form(...),
    reason: ReportReason = Form(...),
    description: str | None = Form(None),
    current_user: User = Depends(require_normal_user),
):
    blog = session.get(Blog, blog_id)
    if not blog or blog.is_hidden or blog.user_id == current_user.id:
        return RedirectResponse(url="/", status_code=303)

    existing_report = session.scalar(
        select(Report).where(
            Report.reporter_id == current_user.id,
            Report.blog_id == blog_id,
        )
    )
    if existing_report:
        return RedirectResponse(url="/", status_code=303)

    create_report = Report(
        reporter_id=current_user.id,
        blog_id=blog_id,
        reason=reason,
        description=description,
    )

    try:
        session.add(create_report)
        session.commit()
        session.refresh(create_report)

    except IntegrityError:
        session.rollback()
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url="/", status_code=303)
