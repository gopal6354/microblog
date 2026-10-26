from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
from database import get_db
from models import Blog, User, Like, Report, Comment
from models.report import ReportReason
from core.config import templates
from dependencies.auth import require_normal_user, require_normal_user_api
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from echohub.services.social_service import (
    MAX_COMMENT_LENGTH,
    annotate_blogs,
    suggested_users,
    visible_comment_count,
)
from echohub.services.notification_service import notify_comment

router = APIRouter()


@router.get("/")
def blogs(request: Request, session: Session = Depends(get_db)):
    current_user = request.state.user
    blogs = session.scalars(
        select(Blog)
        .options(
            selectinload(Blog.user),
            selectinload(Blog.likes),
            selectinload(Blog.comments).selectinload(Comment.user),
        )
        .where(Blog.is_hidden.is_(False))
        .order_by(Blog.created_at.desc())
    ).all()

    annotate_blogs(blogs, current_user)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "blogs": blogs,
            "current_user": current_user,
            "suggested_users": suggested_users(session, current_user),
            "flash": request.session.pop("_flash", None),
        },
    )


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
    if not blog or blog.is_hidden:
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


@router.post("/blog/{blog_id}/comment")
def add_comment(
    blog_id: int,
    request: Request,
    content: str = Form(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user_api),
):
    blog = session.get(Blog, blog_id)
    if not blog or blog.is_hidden:
        return JSONResponse(
            {"success": False, "message": "Post not found"}, status_code=404
        )

    content = content.strip()
    if not content:
        return JSONResponse(
            {"success": False, "message": "Comment cannot be empty."}, status_code=400
        )
    if len(content) > MAX_COMMENT_LENGTH:
        return JSONResponse(
            {
                "success": False,
                "message": f"Comment cannot exceed {MAX_COMMENT_LENGTH} characters.",
            },
            status_code=400,
        )

    comment = Comment(user_id=current_user.id, blog_id=blog_id, content=content)
    session.add(comment)
    notify_comment(session, blog, comment)
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
            "comment_count": visible_comment_count(session, blog_id),
        }
    )


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
