from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import Follow, Notification, User
from models.notification import NotificationType
from models.user import RoleChoice, StatusChoice
from echohub.services.feed_service import hidden_user_ids_query, is_blocked_between
from utils.text import extract_mentions


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


def notify_reply(session: Session, parent, comment):
    if comment.user_id == parent.user_id:
        return
    session.add(
        Notification(
            recipient_id=parent.user_id,
            actor_id=comment.user_id,
            type=NotificationType.REPLY,
            blog_id=comment.blog_id,
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


def notify_follow_request(session: Session, follow_request):
    session.add(
        Notification(
            recipient_id=follow_request.target_id,
            actor_id=follow_request.requester_id,
            type=NotificationType.FOLLOW_REQUEST,
            follow_request=follow_request,
        )
    )


def notification_time(blog):
    # a scheduled post's notifications stay hidden until the post goes live
    now = datetime.utcnow()
    return max(now, blog.published_at) if blog.published_at else now


def notify_repost(session: Session, original, repost):
    """Point at the repost itself so undoing it removes the notification."""
    if repost.user_id == original.user_id:
        return
    session.add(
        Notification(
            recipient_id=original.user_id,
            actor_id=repost.user_id,
            type=NotificationType.REPOST,
            blog=repost,
        )
    )


def notify_mentions(session: Session, actor_id: int, text, blog, comment=None, skip=()):
    """Notify @mentioned users who can see the post; `skip` holds already-notified ids."""
    usernames = extract_mentions(text)
    if not usernames or blog.is_draft:
        return

    author = session.get(User, blog.user_id)
    users = session.scalars(
        select(User).where(
            User.username.in_(usernames),
            User.is_deleted.is_(False),
            User.status == StatusChoice.ACTIVE,
            User.role != RoleChoice.SUPER_ADMIN,
        )
    ).all()
    for user in users:
        if user.id == actor_id or user.id in skip:
            continue
        if is_blocked_between(session, actor_id, user.id):
            continue
        # a private author's post is only visible to their followers
        if author.is_private and user.id != author.id:
            follows_author = session.scalar(
                select(Follow.id).where(
                    Follow.follower_id == user.id, Follow.followed_id == author.id
                )
            )
            if not follows_author:
                continue
        session.add(
            Notification(
                recipient_id=user.id,
                actor_id=actor_id,
                type=NotificationType.MENTION,
                blog=blog,
                comment=comment,
                created_at=notification_time(blog),
            )
        )


def visible_notifications_query(user_id: int):
    # notifications from suspended, blocked or muted users stay hidden, like their content
    return (
        select(Notification)
        .join(User, Notification.actor_id == User.id)
        .where(
            Notification.recipient_id == user_id,
            User.is_deleted.is_(False),
            Notification.actor_id.not_in(hidden_user_ids_query(user_id)),
            Notification.created_at <= datetime.utcnow(),
        )
    )


def unread_notification_count(session: Session, user_id: int):
    query = visible_notifications_query(user_id).where(Notification.is_read.is_(False))
    return session.scalar(select(func.count()).select_from(query.subquery()))
