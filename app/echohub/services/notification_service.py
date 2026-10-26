from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import Notification, User
from models.notification import NotificationType


def notify_comment(session: Session, blog, comment):
    # no notification for commenting on your own post
    if comment.user_id == blog.user_id:
        return
    session.add(
        Notification(
            recipient_id=blog.user_id,
            actor_id=comment.user_id,
            type=NotificationType.COMMENT,
            blog_id=blog.id,
            comment=comment,
        )
    )


def notify_follow(session: Session, follow):
    session.add(
        Notification(
            recipient_id=follow.followed_id,
            actor_id=follow.follower_id,
            type=NotificationType.FOLLOW,
            follow=follow,
        )
    )


def visible_notifications_query(user_id: int):
    # notifications from suspended users stay hidden, like their content
    return (
        select(Notification)
        .join(User, Notification.actor_id == User.id)
        .where(Notification.recipient_id == user_id, User.is_deleted.is_(False))
    )


def unread_notification_count(session: Session, user_id: int):
    query = visible_notifications_query(user_id).where(Notification.is_read.is_(False))
    return session.scalar(select(func.count()).select_from(query.subquery()))
