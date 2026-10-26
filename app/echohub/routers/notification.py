from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from core.config import templates
from database import get_db
from dependencies.auth import require_normal_user
from echohub.services.notification_service import visible_notifications_query
from models import Follow, Notification, User
from models.notification import NotificationType

router = APIRouter()

NOTIFICATION_PAGE_SIZE = 50


@router.get("/notifications")
def notifications_page(
    request: Request,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_normal_user),
):
    notifications = session.scalars(
        visible_notifications_query(current_user.id)
        .options(
            selectinload(Notification.actor),
            selectinload(Notification.blog),
            selectinload(Notification.comment),
        )
        .order_by(Notification.created_at.desc())
        .limit(NOTIFICATION_PAGE_SIZE)
    ).all()

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
            "unread_ids": unread_ids,
            "followed_ids": followed_ids,
            "current_user": current_user,
            "NotificationType": NotificationType,
            "flash": request.session.pop("_flash", None),
        },
    )
