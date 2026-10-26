from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload
from models.blogs import Blog
from models.user import User, RoleChoice
from models.report import ReportStatus, Report
from models.activation_request import AccountActivation, ActivationRequestStatus


def is_blog_exist(blog_id: int, session: Session):
    return session.get(Blog, blog_id)


def is_user_exist(user_id: int, session: Session):
    return session.get(User, user_id)


def update_report_status(
    blog_id: int,
    status: ReportStatus,
    session: Session,
):
    reports = session.scalars(
        select(Report).where(
            Report.blog_id == blog_id,
            Report.status == ReportStatus.PENDING,
        )
    ).all()

    for report in reports:
        report.status = status


def soft_delete_user(user: User):
    user.is_deleted = True
    # invalidate any access tokens already issued to this user
    user.token_version += 1

    for blog in user.blogs:
        if not blog.is_hidden:
            blog.hidden_by_suspension = True
        blog.is_hidden = True


def restore_user(user: User):
    if not user.is_deleted:
        return

    user.is_deleted = False

    for blog in user.blogs:
        if blog.hidden_by_suspension:
            blog.is_hidden = False
            blog.hidden_by_suspension = False


def is_activation_request_exist(activation_id: int, session: Session):
    return session.get(AccountActivation, activation_id)


def activation_status_update(
    activation: AccountActivation,
    status: ActivationRequestStatus,
):
    if activation.status != ActivationRequestStatus.PENDING:
        return False, "This activation request has already been processed."

    if status == ActivationRequestStatus.APPROVED:
        activation.status = ActivationRequestStatus.APPROVED
        restore_user(activation.user)
        return True, "Activation request approved and account restored."

    if status == ActivationRequestStatus.REJECTED:
        activation.status = ActivationRequestStatus.REJECTED
        return True, "Activation request rejected."

    return False, "Invalid status."


def get_dashboard_stats(session: Session):
    return {
        "total_users": session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role != RoleChoice.SUPER_ADMIN)
        ),
        "total_blogs": session.scalar(select(func.count()).select_from(Blog)),
        "pending_reports": session.scalar(
            select(func.count())
            .select_from(Report)
            .where(Report.status == ReportStatus.PENDING)
        ),
        "pending_activation_requests": session.scalar(
            select(func.count())
            .select_from(AccountActivation)
            .where(AccountActivation.status == ActivationRequestStatus.PENDING)
        ),
    }


def get_recent_activity(session: Session, limit: int = 10):
    activities = []

    users = session.scalars(
        select(User)
        .where(User.role != RoleChoice.SUPER_ADMIN)
        .order_by(User.created_at.desc())
        .limit(limit)
    ).all()
    activities += [
        {"user": user, "action": "Joined EchoHub", "date": user.created_at}
        for user in users
    ]

    blogs = session.scalars(
        select(Blog)
        .options(selectinload(Blog.user))
        .order_by(Blog.created_at.desc())
        .limit(limit)
    ).all()
    activities += [
        {"user": blog.user, "action": "Created a new blog", "date": blog.created_at}
        for blog in blogs
    ]

    reports = session.scalars(
        select(Report)
        .options(selectinload(Report.reporter))
        .order_by(Report.created_at.desc())
        .limit(limit)
    ).all()
    activities += [
        {
            "user": report.reporter,
            "action": "Reported a blog",
            "date": report.created_at,
        }
        for report in reports
    ]

    activation_requests = session.scalars(
        select(AccountActivation)
        .options(selectinload(AccountActivation.user))
        .order_by(AccountActivation.created_at.desc())
        .limit(limit)
    ).all()
    activities += [
        {
            "user": activation.user,
            "action": "Requested activation",
            "date": activation.created_at,
        }
        for activation in activation_requests
    ]

    activities.sort(key=lambda activity: activity["date"], reverse=True)
    return activities[:limit]
