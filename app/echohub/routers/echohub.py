from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
from database import get_db
from models import Blog, User, Like, Report
from models.report import ReportReason
from core.config import templates
from dependencies.auth import require_normal_user, require_normal_user_api
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/")
def blogs(request: Request, session: Session = Depends(get_db)):
    current_user = request.state.user
    blogs = session.scalars(
        select(Blog)
        .options(selectinload(Blog.user), selectinload(Blog.likes))
        .where(Blog.is_hidden.is_(False))
        .order_by(Blog.created_at.desc())
    ).all()

    for blog in blogs:
        if current_user:
            blog.is_liked = any(like.user_id == current_user.id for like in blog.likes)
        else:
            blog.is_liked = False

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "blogs": blogs,
            "current_user": current_user,
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
    session.commit()
    like_count = session.scalar(
        select(func.count(Like.id)).where(Like.blog_id == blog_id)
    )

    return JSONResponse({"success": True, "liked": liked, "like_count": like_count})


@router.post("/report/blog")
def report_blog(
    request: Request,
    session: Session = Depends(get_db),
    blog_id: int = Form(...),
    reason: ReportReason = Form(...),
    description: str | None = Form(None),
    current_user: User = Depends(require_normal_user),
):
    blog = session.get(Report, blog_id)
    if blog:
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
