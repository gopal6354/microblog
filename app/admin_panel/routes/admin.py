from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import RedirectResponse
from core.config import templates
from dependencies.auth import require_super_admin
from models.user import RoleChoice
from models import Blog, User, Report
from models.report import ReportStatus
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from database import get_db
from models.activation_request import ActivationRequestStatus, AccountActivation
from utils.flash import flash
from utils.file_upload import delete_file
from utils.pagination import paginate
from admin_panel.services.admin_service import (
    is_blog_exist,
    update_report_status,
    is_user_exist,
    soft_delete_user,
    restore_user,
    is_activation_request_exist,
    activation_status_update,
    get_dashboard_stats,
    get_recent_activity,
)


router = APIRouter()

ADMIN_PAGE_SIZE = 10


# Shows the admin dashboard (super admin only).
# Displays site-wide stats and recent activity.
@router.get("/admin-dashboard")
def admin_dashboard_page(
    request: Request,
    current_user: User = Depends(require_super_admin),
    session: Session = Depends(get_db),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "flash": request.session.pop("_flash", None),
            "stats": get_dashboard_stats(session),
            "recent_activity": get_recent_activity(session),
        },
    )


# Lists all non-admin users for the admin, paginated.
# Active users first, newest first.
@router.get("/admin/users")
def admin_users_page(
    request: Request,
    page: int = Query(1, ge=1),
    current_user: User = Depends(require_super_admin),
    session: Session = Depends(get_db),
):
    pagination = paginate(
        session,
        select(User)
        .where(User.role != RoleChoice.SUPER_ADMIN)
        .order_by(User.is_deleted.asc(), User.created_at.desc(), User.id.desc()),
        page,
        ADMIN_PAGE_SIZE,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/components/users.html",
        context={"all_user": pagination.items, "pagination": pagination},
    )


# Suspends a user (soft delete) and signs them out of every session.
# All their posts are hidden too; super admins can't be suspended.
@router.post("/admin/users/{user_id}/lock")
def suspend_user(
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

    if user.role == RoleChoice.SUPER_ADMIN:
        flash(request, "Super admin accounts cannot be suspended.", "danger")
        return RedirectResponse(
            url="/admin/users",
            status_code=303,
        )

    if user.is_deleted:
        flash(request, "User is already suspended.", "warning")
        return RedirectResponse(
            url="/admin/users",
            status_code=303,
        )

    soft_delete_user(user)

    session.commit()
    flash(request, "User suspended successfully.", "success")

    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )


# Restores a suspended (soft-deleted) user.
# The user can sign in again afterwards.
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


# Permanently deletes a user and everything linked to them.
# Also deletes their profile image and the media of all their posts.
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

    if user.id == current_user.id or user.role == RoleChoice.SUPER_ADMIN:
        flash(request, "Super admin accounts cannot be deleted here.", "danger")
        return RedirectResponse(
            url="/admin/users",
            status_code=303,
        )

    media = [user.profile_image]
    media += [path for blog in user.blogs for path in (blog.image, blog.video)]

    session.delete(user)
    session.commit()

    for path in media:
        delete_file(path)

    flash(request, "User deleted successfully.", "success")

    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )


# Lists all posts for the admin, paginated.
# Loads each post's author and likes for display.
@router.get("/admin/blogs")
def admin_blogs_page(
    request: Request,
    page: int = Query(1, ge=1),
    current_user: User = Depends(require_super_admin),
    session: Session = Depends(get_db),
):
    pagination = paginate(
        session,
        select(Blog)
        .options(selectinload(Blog.user), selectinload(Blog.likes))
        .order_by(Blog.created_at.desc(), Blog.id.desc()),
        page,
        ADMIN_PAGE_SIZE,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/components/blogs.html",
        context={"blogs": pagination.items, "pagination": pagination},
    )


# Hides a post so it no longer appears anywhere on the site.
# The post is kept in the database and can be restored.
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


# Makes a hidden post visible again.
# Redirects back to the admin posts list.
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


# Permanently deletes a post.
# Also deletes its uploaded image or video.
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

    media = [blog.image, blog.video]

    session.delete(blog)
    session.commit()

    for path in media:
        delete_file(path)

    flash(request, "Blog deleted successfully.", "success")

    return RedirectResponse(
        url="/admin/blogs",
        status_code=303,
    )


# Lists posts that have at least one user report, paginated.
# The admin opens one from here to review it.
@router.get("/admin/reports")
def admin_reports_page(
    request: Request,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    pagination = paginate(
        session,
        select(Blog)
        .options(selectinload(Blog.user), selectinload(Blog.reports))
        .where(Blog.reports.any())
        .order_by(Blog.created_at.desc(), Blog.id.desc()),
        page,
        ADMIN_PAGE_SIZE,
    )
    return templates.TemplateResponse(
        request=request,
        name="admin/components/reports.html",
        context={"reported_blogs": pagination.items, "pagination": pagination},
    )


# Shows all reports for one post, with the most recent highlighted.
# Redirects back if the post has no reports.
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

    if not blog or not blog.reports:
        flash(request, "No reports found for this blog.", "warning")
        return RedirectResponse(url="/admin/reports", status_code=303)

    latest_report = max(blog.reports, key=lambda report: report.created_at)
    return templates.TemplateResponse(
        request=request,
        name="admin/components/review_reports.html",
        context={"blog": blog, "latest_report": latest_report},
    )


# Updates the status of a post's reports (e.g. resolved or dismissed).
# Only reports still pending are changed; no action is taken on the post itself.
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


# Lists account activation requests from blocked users, paginated.
# Newest requests first.
@router.get("/admin/activation-requests")
def admin_activation_request_page(
    request: Request,
    page: int = Query(1, ge=1),
    current_user: User = Depends(require_super_admin),
    session: Session = Depends(get_db),
):
    pagination = paginate(
        session,
        select(AccountActivation)
        .options(selectinload(AccountActivation.user))
        .order_by(AccountActivation.created_at.desc(), AccountActivation.id.desc()),
        page,
        ADMIN_PAGE_SIZE,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/components/activation_request.html",
        context={
            "activation_requests": pagination.items,
            "pagination": pagination,
            "ActivationRequestStatus": ActivationRequestStatus,
        },
    )


# Approves or rejects an account activation request.
# Approving reactivates the user's account.
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
        flash(request, "Record not found.", "danger")
        return RedirectResponse(url="/admin/activation-requests", status_code=303)
    success, message = activation_status_update(activation_request, status)

    if not success:
        flash(request, message, "danger")
        return RedirectResponse(url="/admin/activation-requests", status_code=303)

    session.commit()

    flash(request, message, "success")
    return RedirectResponse(url="/admin/activation-requests", status_code=303)
