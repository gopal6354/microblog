from sqlalchemy import select
from sqlalchemy.orm import Session
from models.blogs import Blog
from models.user import User
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

    for blog in user.blogs:
        blog.is_hidden = True


def restore_user(user: User):
    if not user.is_deleted:
        return

    user.is_deleted = False

    for blog in user.blogs:
        blog.is_hidden = False


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
        return True, "Activation request approved."

    if status == ActivationRequestStatus.REJECTED:
        activation.status = ActivationRequestStatus.REJECTED
        return True, "Activation request rejected."

    return False, "Invalid status."
