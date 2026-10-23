from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import RedirectResponse
from core.config import templates
from dependencies.auth import require_super_admin
from models.user import RoleChoice
from models import Blog, User, Report
from models.report import ReportStatus
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload
from database import get_db
import math
from models.activation_request import ActivationRequestStatus, AccountActivation
from utils.flash import flash
from admin_panel.services.admin_service import (
    is_blog_exist,
    update_report_status,
    is_user_exist,
    soft_delete_user,
    restore_user,
    is_activation_request_exist,
    activation_status_update,
)


router = APIRouter()


# admin dashboard page
@router.get("/admin-dashboard")
def admin_dashboard_page(
    request: Request, current_user: User = Depends(require_super_admin)
):
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={"flash": request.session.pop("_flash", None)},
    )


# admin users page
@router.get("/admin/users")
def admin_users_page(
    requst: Request,
    current_user: User = Depends(require_super_admin),
    session: Session = Depends(get_db),
):
    all_users = session.scalars(
        select(User)
        .where(User.role != RoleChoice.SUPER_ADMIN)
        .order_by(User.is_deleted.asc(), User.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request=requst,
        name="admin/components/users.html",
        context={"all_user": all_users},
    )


# soft delete user
@router.post("/admin/users/{user_id}/lock")
def suspend_user(
    user_id: int,
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    user = is_user_exist(user_id, session)

    if not user:
        print("not found")
        flash(request, "User not found.", "danger")
        return RedirectResponse(
            url="/admin/users",
            status_code=303,
        )

    if user.is_deleted:
        print("already deleted")
        flash(request, "User is already suspended.", "warning")
        return RedirectResponse(
            url="/admin/users",
            status_code=303,
        )

    soft_delete_user(user)

    session.commit()
    print("success")
    flash(request, "User suspended successfully.", "success")

    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )


# soft delete user restore
@router.post("/admin/users/{user_id}/restore")
def admin_restore_user(
    request: Request,
    user_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    user = is_user_exist(user_id, session)
    if not user:
        flash(request, "User not found.", "danger")
        return RedirectResponse(
            url="/admin/users",
            status_code=303,
        )
    restore_user(user)

    session.commit()
    flash(request, "User restore successfully.", "success")
    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )


# hard delete user
@router.post("/admin/users/{user_id}/delete")
def delete_user(
    user_id: int,
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    user = is_user_exist(user_id, session)

    if not user:
        flash(request, "User not found.", "danger")
        return RedirectResponse(
            url="/admin/users",
            status_code=303,
        )

    session.delete(user)
    session.commit()

    flash(request, "User deleted successfully.", "success")

    return RedirectResponse(
        url="/admin/users",
        status_code=303,
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


# soft delete blog
@router.post("/admin/blogs/{blog_id}/hide")
def hide_blog(
    blog_id: int,
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    blog = is_blog_exist(blog_id, session)

    if not blog:
        flash(request, "Blog not found.", "danger")
        return RedirectResponse(
            url="/admin/blogs",
            status_code=303,
        )

    if blog.is_hidden:
        flash(request, "Blog is already hidden.", "warning")
        return RedirectResponse(
            url="/admin/blogs",
            status_code=303,
        )

    blog.is_hidden = True

    session.commit()

    flash(request, "Blog hidden successfully.", "success")

    return RedirectResponse(
        url="/admin/blogs",
        status_code=303,
    )


@router.post("/admin/blogs/{blog_id}/restore")
def admin_blogs_restore(
    request: Request,
    blog_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    blog = is_blog_exist(blog_id, session)

    if not blog:
        flash(request, "Blog not found.", "danger")
        return RedirectResponse(
            url="/admin/blogs",
            status_code=303,
        )

    blog.is_hidden = False

    session.commit()
    return RedirectResponse(url="/admin/blogs", status_code=303)


# hard delete blog
@router.post("/admin/blogs/{blog_id}/delete")
def delete_blog(
    blog_id: int,
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    blog = session.get(Blog, blog_id)

    if not blog:
        flash(request, "Blog not found.", "danger")
        return RedirectResponse(
            url="/admin/blogs",
            status_code=303,
        )

    session.delete(blog)
    session.commit()

    flash(request, "Blog deleted successfully.", "success")

    return RedirectResponse(
        url="/admin/blogs",
        status_code=303,
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
@router.post("/admin/reports/{blog_id}/status")
def admin_update_report_status(
    blog_id: int,
    request: Request,
    status: ReportStatus = Form(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    blog = is_blog_exist(blog_id, session)

    if not blog:
        flash(request, "Blog not found.", "danger")
        return RedirectResponse(
            url="/admin/reports",
            status_code=303,
        )

    update_report_status(
        blog_id=blog_id,
        status=status,
        session=session,
    )

    session.commit()

    flash(request, "Report status updated successfully.", "success")

    return RedirectResponse(
        url="/admin/reports",
        status_code=303,
    )


# admin account activation page
@router.get("/admin/activation-requests")
def admin_activation_request_page(
    request: Request,
    current_user: User = Depends(require_super_admin),
    session: Session = Depends(get_db),
):
    activation_request = session.scalars(
        select(AccountActivation).options(selectinload(AccountActivation.user))
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/components/activation_request.html",
        context={
            "activation_requests": activation_request,
            "ActivationRequestStatus": ActivationRequestStatus,
        },
    )


@router.post("/admin/account-activation/{activation_id}/update")
def admin_account_activation_update(
    activation_id: int,
    request: Request,
    status: ActivationRequestStatus = Form(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    activation_request = is_activation_request_exist(activation_id, session)
    if not activation_request:
        print("not found")
        flash(request, "Record not found.", "danger")
        return RedirectResponse(url="/admin/activation-requests")
    print(status)
    success, message = activation_status_update(activation_request, status)

    if not success:
        print("false")
        flash(request, message, "danger")
        return RedirectResponse(url="/admin/activation-requests", status_code=303)

    session.commit()

    flash(request, message, "success")
    print("success")
    return RedirectResponse(url="/admin/activation-requests", status_code=303)
