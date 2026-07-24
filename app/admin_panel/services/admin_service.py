from sqlalchemy import select
from sqlalchemy.orm import Session
from models.blogs import Blog
from models.user import User
from models.report import ReportStatus, Report, ModerationAction


def is_blog_exist(blog_id: int, session: Session):
    return session.get(Blog, blog_id)


def update_report_moderate(
    blog_id: int,
    status: ReportStatus,
    action: ModerationAction,
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
        report.action = action
    print("status and action updated")
    return reports


def validate_moderation(
    status: ReportStatus,
    action: ModerationAction,
) -> tuple[bool, str | None]:
    if status == ReportStatus.PENDING and action != ModerationAction.NONE:
        return False, "Pending reports cannot have a moderation action."

    if status == ReportStatus.DISMISSED and action != ModerationAction.NONE:
        return False, "Dismissed reports must have action 'None'."

    if status == ReportStatus.RESOLVED and action == ModerationAction.NONE:
        return False, "Resolved reports require a moderation action."

    return True, None


def perform_moderation_action(
    blog: Blog,
    action: ModerationAction,
    session: Session,
):
    if action == ModerationAction.NONE:
        return

    elif action == ModerationAction.BLOG_SOFT_DELETED:
        blog_soft_delete(blog)

    elif action == ModerationAction.BLOG_HARD_DELETED:
        blog_hard_delete(blog, session)

    elif action == ModerationAction.AUTHOR_SUSPENDED:
        user_soft_delete(blog.user)

    elif action == ModerationAction.AUTHOR_DELETED:
        user_hard_delete(blog.user, session=session)


def blog_soft_delete(blog: Blog):
    blog.is_hidden = True


def blog_hard_delete(blog: Blog, session: Session):
    session.delete(blog)


def user_soft_delete(user: User):
    user.is_deleted = True

    for user_blog in user.blogs:
        user_blog.is_hidden = True


def user_hard_delete(user: User, session: Session):
    session.delete(user)
