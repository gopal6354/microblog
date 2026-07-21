from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from database import get_db
from models import Blog, User, Like
from core.config import templates
from dependencies.auth import get_current_user
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/")
def blogs(request: Request, session: Session = Depends(get_db)):
    current_user = request.state.user
    blogs = session.scalars(
        select(Blog)
        .options(selectinload(Blog.user), selectinload(Blog.likes))
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
        context={"blogs": blogs, "current_user": current_user},
    )


@router.post("/blog/{blog_id}/like")
def like_blog(
    blog_id: int,
    request: Request,
    session: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
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
