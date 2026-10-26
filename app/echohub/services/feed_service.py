from datetime import datetime, timedelta

from sqlalchemy import select, func, or_, and_, union
from sqlalchemy.orm import Session, aliased, selectinload

from models import Blog, Block, Comment, Follow, Mute, Tag, User, blog_tags

FEED_PAGE_SIZE = 10


def hidden_user_ids_query(viewer_id: int, include_muted: bool = True):
    """Users whose content the viewer shouldn't see: blocked either way, or muted."""
    queries = [
        select(Block.blocked_id).where(Block.blocker_id == viewer_id),
        select(Block.blocker_id).where(Block.blocked_id == viewer_id),
    ]
    if include_muted:
        queries.append(select(Mute.muted_id).where(Mute.muter_id == viewer_id))
    return union(*queries)


def hidden_user_ids(session: Session, viewer: User | None) -> set[int]:
    if not viewer:
        return set()
    return set(session.scalars(hidden_user_ids_query(viewer.id)).all())


def is_blocked_between(session: Session, user_a_id: int, user_b_id: int):
    return (
        session.scalar(
            select(Block.id).where(
                or_(
                    and_(Block.blocker_id == user_a_id, Block.blocked_id == user_b_id),
                    and_(Block.blocker_id == user_b_id, Block.blocked_id == user_a_id),
                )
            )
        )
        is not None
    )


def _live(blog_cls):
    return and_(blog_cls.is_hidden.is_(False), blog_cls.is_draft.is_(False))


def _audience(author_cls, viewer: User | None):
    """Public authors, plus private ones the viewer follows (or is)."""
    if not viewer:
        return author_cls.is_private.is_(False)
    followed_ids = select(Follow.followed_id).where(Follow.follower_id == viewer.id)
    return or_(
        author_cls.is_private.is_(False),
        author_cls.id == viewer.id,
        author_cls.id.in_(followed_ids),
    )


def visible_blogs_query(viewer: User | None, include_muted: bool = False):
    """Posts the viewer may see, with what the post card needs eager loaded.

    Excludes hidden and draft posts, suspended and blocked/muted
    authors, private authors the viewer doesn't follow, and reposts whose
    original fails any of those checks. `include_muted` keeps muted authors,
    for when the viewer goes looking for them (their profile, a direct link).
    """
    original = aliased(Blog)
    original_author = aliased(User)

    card_options = (
        selectinload(Blog.user),
        selectinload(Blog.likes),
        selectinload(Blog.comments).selectinload(Comment.user),
    )
    query = (
        select(Blog)
        .join(User, Blog.user_id == User.id)
        .outerjoin(original, Blog.repost_of_id == original.id)
        .outerjoin(original_author, original.user_id == original_author.id)
        .options(
            *card_options,
            selectinload(Blog.repost_of).options(*card_options),
        )
        .where(
            _live(Blog),
            User.is_deleted.is_(False),
            _audience(User, viewer),
            or_(
                Blog.repost_of_id.is_(None),
                and_(
                    _live(original),
                    original_author.is_deleted.is_(False),
                    _audience(original_author, viewer),
                ),
            ),
        )
    )

    if viewer:
        hidden = hidden_user_ids_query(viewer.id, include_muted=not include_muted)
        query = query.where(
            Blog.user_id.not_in(hidden),
            or_(original.id.is_(None), original.user_id.not_in(hidden)),
        )
    return query


def newest_first(query):
    return query.order_by(Blog.published_at.desc(), Blog.id.desc())


def can_view_blog(session: Session, viewer: User | None, blog: Blog | None):
    if blog is None:
        return False
    query = visible_blogs_query(viewer, include_muted=True).where(Blog.id == blog.id)
    return session.scalar(query.with_only_columns(Blog.id)) is not None


def can_view_profile_content(session: Session, viewer: User | None, profile: User):
    """Whether the viewer may see a profile's posts and follow lists."""
    if not profile.is_private or (viewer and viewer.id == profile.id):
        return True
    if not viewer:
        return False
    return (
        session.scalar(
            select(Follow.id).where(
                Follow.follower_id == viewer.id, Follow.followed_id == profile.id
            )
        )
        is not None
    )


def trending_tags(session: Session, limit: int = 5, days: int = 7):
    """Most used tags on public posts over the last few days, as (name, count)."""
    now = datetime.utcnow()
    count = func.count(blog_tags.c.blog_id).label("post_count")
    return session.execute(
        select(Tag.name, count)
        .join(blog_tags, blog_tags.c.tag_id == Tag.id)
        .join(Blog, Blog.id == blog_tags.c.blog_id)
        .join(User, Blog.user_id == User.id)
        .where(
            _live(Blog),
            Blog.published_at >= now - timedelta(days=days),
            User.is_deleted.is_(False),
            User.is_private.is_(False),
        )
        .group_by(Tag.name)
        .order_by(count.desc(), Tag.name)
        .limit(limit)
    ).all()
