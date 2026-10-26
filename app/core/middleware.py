from fastapi import Request
from jose import JWTError

from core.config import decode_token
from database import Session
from models.user import User
from echohub.services.notification_service import unread_notification_count


async def auth_middleware(request: Request, call_next):
    request.state.user = None
    request.state.unread_notifications = 0
    deleted_user = False

    token = request.cookies.get("access_token")

    if token:
        try:
            payload = decode_token(token)

            if payload.get("type") != "access":
                raise JWTError("Invalid token type")

            user_id = int(payload.get("sub"))

            session = Session()
            try:
                user = session.get(User, user_id)
                if user:
                    if user.is_deleted or payload.get("ver", 0) != user.token_version:
                        deleted_user = True
                    else:
                        request.state.user = user
                        request.state.unread_notifications = unread_notification_count(
                            session, user.id
                        )

            finally:
                session.close()

        except (JWTError, ValueError, TypeError):
            pass

    response = await call_next(request)

    if deleted_user:
        response.delete_cookie("access_token")

    return response
