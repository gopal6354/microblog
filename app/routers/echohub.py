from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from database import get_db
from models.blogs import Blog
from core.config import templates

router = APIRouter()


@router.get("/")
def blogs(request: Request, session: Session = Depends(get_db)):
    blogs = session.scalars(
        select(Blog).options(selectinload(Blog.user)).order_by(Blog.created_at.desc())
    ).all()
    print("create blog")
    return templates.TemplateResponse(
        request=request, name="home.html", context={"blogs": blogs}
    )
