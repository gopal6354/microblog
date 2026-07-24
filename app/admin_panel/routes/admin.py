from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import RedirectResponse
from core.config import templates
from dependencies.auth import require_super_admin
from models.user import RoleChoice
from models import Blog, User, Report
from models.report import ReportStatus, ModerationAction
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload
from admin_panel.services.admin_service import (
    is_blog_exist,
    update_report_moderate,
    validate_moderation,
    perform_moderation_action,
)
from database import get_db
import math


router = APIRouter()


# admin dashboard page
@router.get("/admin-dashboard")
def admin_dashboard_page(
    request: Request, current_user: User = Depends(require_super_admin)
):
    return templates.TemplateResponse(request=request, name="admin/dashboard.html")


# admin users page
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


# admin blogs page
@router.get("/admin/blogs")
def admin_blogs_page(
    request: Request,
    page: int = Query(1, ge=1),
    current_user: User = Depends(require_super_admin),
    session: Session = Depends(get_db),
):
    per_page = 10
    offset = (page - 1) * per_page

    blogs = session.scalars(
        select(Blog)
        .options(selectinload(Blog.user), selectinload(Blog.likes))
        .order_by(Blog.created_at.desc())
        .limit(per_page)
        .offset(offset)
    ).all()

    total_blogs = session.scalar(select(func.count()).select_from(Blog))
    total_pages = max(1, math.ceil(total_blogs / per_page))

    return templates.TemplateResponse(
        request=request,
        name="admin/components/blogs.html",
        context={"blogs": blogs, "page": page, "total_pages": total_pages},
    )


# admin reports page
@router.get("/admin/reports")
def admin_reports_page(
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    reports_blogs = session.scalars(
        select(Blog)
        .options(selectinload(Blog.user), selectinload(Blog.reports))
        .where(Blog.reports.any())
        .order_by(Blog.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/components/reports.html",
        context={"reported_blogs": reports_blogs},
    )


# admin review report page
@router.get("/admin/reports/{blog_id}")
def review_report_page(
    blog_id: int,
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    blog = session.scalar(
        select(Blog)
        .options(
            selectinload(Blog.user),
            selectinload(Blog.reports).selectinload(Report.reporter),
        )
        .where(Blog.id == blog_id)
    )

    latest_report = max(blog.reports, key=lambda report: report.created_at)
    return templates.TemplateResponse(
        request=request,
        name="admin/components/review_reports.html",
        context={"blog": blog, "latest_report": latest_report},
    )


# admin review report status and action update page
@router.post("/admin/reports/{blog_id}/moderate")
def moderate_report(
    blog_id: int,
    request: Request,
    status: ReportStatus = Form(...),
    action: ModerationAction = Form(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    blog = is_blog_exist(blog_id, session)

    if not blog:
        return RedirectResponse(url="/admin/reports", status_code=303)

    is_valid, error = validate_moderation(status, action)

    if not is_valid:
        return templates.TemplateResponse(
            request=request,
            name="admin/components/review_reports.html",
            context={
                "blog": blog,
                "latest_report": blog.reports[-1],
                "error": error,
            },
        )

    update_report_moderate(
        blog_id=blog_id, status=status, action=action, session=session
    )

    perform_moderation_action(
        blog=blog,
        action=action,
        session=session,
    )

    session.commit()
    print("success")
    return RedirectResponse(url="/admin/reports/", status_code=303)


# admin account activation page
@router.get("/admin/activation-requests")
def admin_activation_request_page(
    request: Request, current_user: User = Depends(require_super_admin)
):
    return templates.TemplateResponse(
        request=request, name="admin/components/activation_request.html"
    )
