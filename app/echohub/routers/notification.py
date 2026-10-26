from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from core.config import templates
from database import get_db
from dependencies.auth import require_normal_user
from echohub.services.notification_service import visible_notifications_query
from models import Blog, Follow, Notification, User
from models.notification import NotificationType
from utils.pagination import paginate

router = APIRouter()

NOTIFICATION_PAGE_SIZE = 50


# Shows the logged-in user's notifications, paginated.
# Marks them all as read but highlights the ones that were unread.
@router.get("/notifications")
def notifications_page(
    request: Request,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    pagination = paginate(
        session,
        visible_notifications_query(current_user.id)
        .options(
            selectinload(Notification.actor),
            selectinload(Notification.blog).selectinload(Blog.repost_of),
            selectinload(Notification.comment),
            selectinload(Notification.follow_request),
        )
        .order_by(Notification.created_at.desc(), Notification.id.desc()),
        page,
        NOTIFICATION_PAGE_SIZE,
    )
    notifications = pagination.items

    # remember what was new before marking everything read, for highlighting
    unread_ids = {n.id for n in notifications if not n.is_read}

    followed_ids = set(
        session.scalars(
            select(Follow.followed_id).where(Follow.follower_id == current_user.id)
        ).all()
    )

    session.execute(
        update(Notification)
        .where(
            Notification.recipient_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    session.commit()
    request.state.unread_notifications = 0

    return templates.TemplateResponse(
        request=request,
        name="/notifications/notifications.html",
        context={
            "notifications": notifications,
            "pagination": pagination,
            "unread_ids": unread_ids,
            "followed_ids": followed_ids,
            "current_user": current_user,
            "NotificationType": NotificationType,
            "flash": request.session.pop("_flash", None),
        },
    )
