from collections import defaultdict

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import Blog, Bookmark, Comment, Follow, FollowRequest, User
from models.user import RoleChoice, StatusChoice
from echohub.services.feed_service import hidden_user_ids, hidden_user_ids_query

MAX_COMMENT_LENGTH = 500


def annotate_blogs(session: Session, blogs, current_user):
    """Set per-viewer fields the post card template relies on.

    A plain repost shows the original's card, so the original is annotated.
    """
    posts = {}
    for blog in blogs:
        post = blog.repost_of if blog.is_plain_repost else blog
        posts[post.id] = post
    post_ids = list(posts)
    if not post_ids:
        return

    hidden = hidden_user_ids(session, current_user)
    bookmarked, reposted = set(), set()
    if current_user:
        bookmarked = set(
            session.scalars(
                select(Bookmark.blog_id).where(
                    Bookmark.user_id == current_user.id,
                    Bookmark.blog_id.in_(post_ids),
                )
            ).all()
        )
        reposted = set(
            session.scalars(
                select(Blog.repost_of_id).where(
                    Blog.user_id == current_user.id,
                    Blog.repost_of_id.in_(post_ids),
                    Blog.content == "",
                )
            ).all()
        )
    repost_counts = dict(
        session.execute(
            select(Blog.repost_of_id, func.count(Blog.id))
            .where(Blog.repost_of_id.in_(post_ids), Blog.is_hidden.is_(False))
            .group_by(Blog.repost_of_id)
        ).all()
    )

    for post in posts.values():
        post.is_liked = bool(current_user) and any(
            like.user_id == current_user.id for like in post.likes
        )
        post.is_bookmarked = post.id in bookmarked
        post.is_reposted = post.id in reposted
        post.repost_count = repost_counts.get(post.id, 0)

        # comments from suspended, blocked or muted users stay hidden, like their posts
        comments = [
            c
            for c in post.comments
            if not c.user.is_deleted and c.user_id not in hidden
        ]
        replies = defaultdict(list)
        for c in comments:
            if c.parent_id:
                replies[c.parent_id].append(c)
        post.visible_comments = [c for c in comments if c.parent_id is None]
        for c in post.visible_comments:
            c.visible_replies = replies[c.id]
        post.comment_count = sum(
            1 + len(c.visible_replies) for c in post.visible_comments
        )


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


def has_requested_follow(session: Session, requester: User | None, target_id: int):
    if not requester:
        return False
    return (
        session.scalar(
            select(FollowRequest.id).where(
                FollowRequest.requester_id == requester.id,
                FollowRequest.target_id == target_id,
            )
        )
        is not None
    )


def requested_ids(session: Session, requester: User | None):
    if not requester:
        return set()
    return set(
        session.scalars(
            select(FollowRequest.target_id).where(
                FollowRequest.requester_id == requester.id
            )
        ).all()
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
        query = query.where(
            User.id != current_user.id,
            User.id.not_in(followed_ids),
            User.id.not_in(hidden_user_ids_query(current_user.id)),
        )
    return session.scalars(query.order_by(User.created_at.desc()).limit(limit)).all()
