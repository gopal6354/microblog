from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session

from core.config import templates
from database import get_db
from dependencies.auth import require_normal_user
from echohub.services.feed_service import (
    FEED_PAGE_SIZE,
    hidden_user_ids_query,
    newest_first,
    visible_blogs_query,
)
from echohub.services.social_service import (
    annotate_blogs,
    requested_ids,
    suggested_users,
)
from models import Blog, Bookmark, Follow, Tag, User
from models.user import RoleChoice, StatusChoice
from utils.pagination import paginate
from utils.text import HASHTAG_RE

router = APIRouter()

SEARCH_TABS = ("posts", "people")
MAX_QUERY_LENGTH = 100


def like_pattern(term: str):
    # treat % and _ in the search box literally
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def followed_ids(session: Session, user: User | None):
    if not user:
        return set()
    return set(
        session.scalars(
            select(Follow.followed_id).where(Follow.follower_id == user.id)
        ).all()
    )


# Searches posts or people (tab=people) by text.
# A query that is just a #hashtag redirects straight to that tag's page.
@router.get("/search")
def search(
    request: Request,
    q: str = "",
    tab: str = "posts",
    page: int = Query(1, ge=1),
    session: Session = Depends(get_db),
):
    current_user = request.state.user
    q = q.strip()[:MAX_QUERY_LENGTH]
    tab = tab if tab in SEARCH_TABS else "posts"

    # searching for a single #tag goes straight to the tag page
    tag_match = HASHTAG_RE.fullmatch(q)
    if tag_match:
        return RedirectResponse(
            url=f"/tag/{tag_match.group(1).lower()}", status_code=303
        )

    pagination = None
    if q:
        pattern = like_pattern(q)
        if tab == "people":
            query = select(User).where(
                User.is_deleted.is_(False),
                User.status == StatusChoice.ACTIVE,
                User.role != RoleChoice.SUPER_ADMIN,
                or_(
                    User.username.ilike(pattern, escape="\\"),
                    User.full_name.ilike(pattern, escape="\\"),
                ),
            )
            if current_user:
                query = query.where(
                    User.id.not_in(
                        hidden_user_ids_query(current_user.id, include_muted=False)
                    )
                )
            pagination = paginate(
                session, query.order_by(User.username), page, FEED_PAGE_SIZE
            )
        else:
            query = visible_blogs_query(current_user).where(
                Blog.content.ilike(pattern, escape="\\")
            )
            pagination = paginate(session, newest_first(query), page, FEED_PAGE_SIZE)
            annotate_blogs(session, pagination.items, current_user)

    return templates.TemplateResponse(
        request=request,
        name="discover/search.html",
        context={
            "q": q,
            "tab": tab,
            "pagination": pagination,
            "results": pagination.items if pagination else [],
            "current_user": current_user,
            "followed_ids": followed_ids(session, current_user),
            "requested_ids": requested_ids(session, current_user),
            "suggested_users": suggested_users(session, current_user),
            "flash": request.session.pop("_flash", None),
        },
    )


# Lists visible posts that use a given hashtag, paginated.
# Shows an empty list if the tag doesn't exist.
@router.get("/tag/{name}")
def tag_page(
    request: Request,
    name: str,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_db),
):
    current_user = request.state.user
    name = name.lower()
    tag = session.scalar(select(Tag).where(Tag.name == name))

    query = visible_blogs_query(current_user).where(
        Blog.tags.any(Tag.id == (tag.id if tag else -1))
    )
    pagination = paginate(session, newest_first(query), page, FEED_PAGE_SIZE)
    annotate_blogs(session, pagination.items, current_user)

    return templates.TemplateResponse(
        request=request,
        name="discover/tag.html",
        context={
            "tag_name": name,
            "blogs": pagination.items,
            "pagination": pagination,
            "current_user": current_user,
            "suggested_users": suggested_users(session, current_user),
            "flash": request.session.pop("_flash", None),
        },
    )


# Lists the posts the logged-in user has bookmarked.
# Most recently bookmarked first, paginated.
@router.get("/bookmarks")
def bookmarks_page(
    request: Request,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    query = (
        visible_blogs_query(current_user, include_muted=True)
        .join(
            Bookmark,
            and_(Bookmark.blog_id == Blog.id, Bookmark.user_id == current_user.id),
        )
        .order_by(Bookmark.created_at.desc(), Bookmark.id.desc())
    )
    pagination = paginate(session, query, page, FEED_PAGE_SIZE)
    annotate_blogs(session, pagination.items, current_user)

    return templates.TemplateResponse(
        request=request,
        name="discover/bookmarks.html",
        context={
            "blogs": pagination.items,
            "pagination": pagination,
            "current_user": current_user,
            "suggested_users": suggested_users(session, current_user),
            "flash": request.session.pop("_flash", None),
        },
    )
