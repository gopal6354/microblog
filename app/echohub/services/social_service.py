from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import Comment, Follow, User
from models.user import RoleChoice, StatusChoice

MAX_COMMENT_LENGTH = 500


def annotate_blogs(blogs, current_user):
    """Set per-viewer fields the post card template relies on."""
    for blog in blogs:
        blog.is_liked = bool(current_user) and any(
            like.user_id == current_user.id for like in blog.likes
        )
        # comments from suspended users stay hidden, like their posts
        blog.visible_comments = [c for c in blog.comments if not c.user.is_deleted]


def visible_comment_count(session: Session, blog_id: int):
    return session.scalar(
        select(func.count(Comment.id))
        .join(User, Comment.user_id == User.id)
        .where(Comment.blog_id == blog_id, User.is_deleted.is_(False))
    )


def follow_counts(session: Session, user_id: int):
    followers = session.scalar(
        select(func.count(Follow.id)).where(Follow.followed_id == user_id)
    )
    following = session.scalar(
        select(func.count(Follow.id)).where(Follow.follower_id == user_id)
    )
    return followers, following


def is_following(session: Session, follower: User | None, followed_id: int):
    if not follower:
        return False
    return (
        session.scalar(
            select(Follow.id).where(
                Follow.follower_id == follower.id, Follow.followed_id == followed_id
            )
        )
        is not None
    )


def can_be_followed(user: User | None):
    return (
        bool(user)
        and not user.is_deleted
        and user.status == StatusChoice.ACTIVE
        and user.role != RoleChoice.SUPER_ADMIN
    )


def suggested_users(session: Session, current_user: User | None, limit: int = 3):
    query = select(User).where(
        User.is_deleted.is_(False),
        User.status == StatusChoice.ACTIVE,
        User.role != RoleChoice.SUPER_ADMIN,
    )
    if current_user:
        followed_ids = select(Follow.followed_id).where(
            Follow.follower_id == current_user.id
        )
        query = query.where(User.id != current_user.id, User.id.not_in(followed_ids))
    return session.scalars(query.order_by(User.created_at.desc()).limit(limit)).all()
