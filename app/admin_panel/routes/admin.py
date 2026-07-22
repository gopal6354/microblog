from fastapi import APIRouter, Request, Depends
from core.config import templates
from dependencies.auth import require_super_admin
from models.user import RoleChoice
from models import Blog, User
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from database import get_db


router = APIRouter()


@router.get("/admin-dashboard")
def admin_dashboard_page(
    request: Request, current_user: User = Depends(require_super_admin)
):
    return templates.TemplateResponse(request=request, name="admin/dashboard.html")


@router.get("/admin/users")
def admin_users_page(
    requst: Request,
    current_user: User = Depends(require_super_admin),
    session: Session = Depends(get_db),
):
    all_users = session.scalars(select(User).where(User.role != RoleChoice.SUPER_ADMIN))

    return templates.TemplateResponse(
        request=requst,
        name="admin/components/users.html",
        context={"all_user": all_users},
    )


@router.get("/admin/blogs")
def admin_blogs_page(
    request: Request,
    current_user: User = Depends(require_super_admin),
    session: Session = Depends(get_db),
):
    blogs = session.scalars(
        select(Blog)
        .options(selectinload(Blog.user), selectinload(Blog.likes))
        .order_by(Blog.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request=request, name="admin/components/blogs.html", context={"blogs": blogs}
    )


@router.get("/admin/reports")
def admin_reports_page(
    request: Request, current_user: User = Depends(require_super_admin)
):
    return templates.TemplateResponse(
        request=request, name="admin/components/reports.html"
    )


@router.get("/admin/activation-requests")
def admin_activation_request_page(
    request: Request, current_user: User = Depends(require_super_admin)
):
    return templates.TemplateResponse(
        request=request, name="admin/components/activation_request.html"
    )
